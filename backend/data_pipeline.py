from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

import feedparser
import pandas as pd
import requests
import time

try:
	import yaml  # type: ignore
except Exception:
	yaml = None

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CONFIG_PATH = os.path.join(_BASE_DIR, "config.yaml")


def _read_config() -> Dict[str, Any]:
	if yaml is None:
		return {}
	if not os.path.exists(_CONFIG_PATH):
		return {}
	with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
		return yaml.safe_load(f) or {}


_cfg = _read_config()
_data_cfg = _cfg.get("data", {}) if isinstance(_cfg, dict) else {}
_providers_cfg = _cfg.get("providers", {}) if isinstance(_cfg, dict) else {}

# Route prices/fundamentals to portfolio_db; news to news_cache_db
_PRICES_DB_PATH = os.path.join(_BASE_DIR, "data", "portfolio.db")
_NEWS_DB_PATH = os.path.join(_BASE_DIR, "data", "news_cache.db")

if isinstance(_data_cfg, dict):
	if _data_cfg.get("portfolio_db"):
		_PRICES_DB_PATH = os.path.join(_BASE_DIR, _data_cfg.get("portfolio_db")) if not os.path.isabs(_data_cfg.get("portfolio_db")) else _data_cfg.get("portfolio_db")
	if _data_cfg.get("news_cache_db"):
		_NEWS_DB_PATH = os.path.join(_BASE_DIR, _data_cfg.get("news_cache_db")) if not os.path.isabs(_data_cfg.get("news_cache_db")) else _data_cfg.get("news_cache_db")

for _p in [_PRICES_DB_PATH, _NEWS_DB_PATH]:
	os.makedirs(os.path.dirname(_p), exist_ok=True)


@contextmanager
def _db(db_path: str) -> Iterable[sqlite3.Connection]:
	conn = sqlite3.connect(db_path)
	try:
		conn.execute("PRAGMA journal_mode=WAL;")
		conn.execute("PRAGMA synchronous=NORMAL;")
		yield conn
		conn.commit()
	finally:
		conn.close()


def _init_prices_db() -> None:
	with _db(_PRICES_DB_PATH) as conn:
		conn.execute(
			"""
			CREATE TABLE IF NOT EXISTS prices (
				id INTEGER PRIMARY KEY AUTOINCREMENT,
				symbol TEXT NOT NULL,
				date TEXT NOT NULL,
				open REAL,
				high REAL,
				low REAL,
				close REAL,
				adj_close REAL,
				volume INTEGER,
				UNIQUE(symbol, date)
			);
			"""
		)
		conn.execute(
			"""
			CREATE TABLE IF NOT EXISTS fundamentals (
				id INTEGER PRIMARY KEY AUTOINCREMENT,
				symbol TEXT NOT NULL,
				key TEXT NOT NULL,
				value TEXT,
				as_of TEXT NOT NULL,
				UNIQUE(symbol, key)
			);
			"""
		)


def _init_news_db() -> None:
	with _db(_NEWS_DB_PATH) as conn:
		conn.execute(
			"""
			CREATE TABLE IF NOT EXISTS news (
				id INTEGER PRIMARY KEY AUTOINCREMENT,
				symbol TEXT,
				title TEXT NOT NULL,
				url TEXT NOT NULL,
				published TEXT,
				summary TEXT,
				source TEXT,
				UNIQUE(url)
			);
			"""
		)


@dataclass
class PriceBar:
	symbol: str
	date: str
	open: float
	high: float
	low: float
	close: float
	adj_close: float
	volume: int


def _utcnow_iso() -> str:
	return datetime.now(timezone.utc).isoformat()


def fetch_prices(symbols: List[str], period: str = "1y", interval: str = "1d") -> List[PriceBar]:
	if not symbols:
		return []
	# Prefer Finnhub for batch daily prices
	if isinstance(_providers_cfg, dict) and (_providers_cfg.get("finnhub", {}) or {}).get("enabled", True):
		return _fetch_prices_finnhub(symbols)
	# Fallback: Twelve Data daily time series (compact)
	return _fetch_prices_twelvedata(symbols)


def _fetch_prices_finnhub(symbols: List[str]) -> List[PriceBar]:
	api_key = ((_providers_cfg.get("finnhub", {}) or {}).get("api_key") or os.getenv("FINNHUB_API_KEY", ""))
	base_url = "https://finnhub.io/api/v1/stock/candle"
	# Pull last ~100 trading days
	end = int(time.time())
	start = end - 120 * 24 * 3600
	all_bars: List[PriceBar] = []
	for symbol in symbols:
		params = {
			"symbol": symbol,
			"resolution": "D",
			"from": start,
			"to": end,
			"token": api_key,
		}
		try:
			resp = requests.get(base_url, params=params, timeout=30)
			resp.raise_for_status()
			data = resp.json() or {}
			if data.get("s") != "ok":
				continue
			t = data.get("t", [])
			o = data.get("o", [])
			h = data.get("h", [])
			l = data.get("l", [])
			c = data.get("c", [])
			v = data.get("v", [])
			for i in range(min(len(t), len(o), len(h), len(l), len(c), len(v))):
				date_str = datetime.utcfromtimestamp(int(t[i])).strftime("%Y-%m-%d")
				all_bars.append(
					PriceBar(
						symbol=symbol,
						date=date_str,
						open=float(o[i] or 0.0),
						high=float(h[i] or 0.0),
						low=float(l[i] or 0.0),
						close=float(c[i] or 0.0),
						adj_close=float(c[i] or 0.0),
						volume=int(v[i] or 0),
					)
				)
		except Exception:
			continue
	return all_bars


def _fetch_prices_twelvedata(symbols: List[str]) -> List[PriceBar]:
	api_key = ((_providers_cfg.get("twelvedata", {}) or {}).get("api_key") or os.getenv("TWELVEDATA_API_KEY", ""))
	base_url = "https://api.twelvedata.com/time_series"
	all_bars: List[PriceBar] = []
	for symbol in symbols:
		params = {
			"symbol": symbol,
			"interval": "1day",
			"outputsize": 100,
			"apikey": api_key,
		}
		try:
			resp = requests.get(base_url, params=params, timeout=30)
			resp.raise_for_status()
			payload = resp.json() or {}
			values = (payload.get("values") or [])
			for row in values:
				all_bars.append(
					PriceBar(
						symbol=symbol,
						date=str(row.get("datetime")),
						open=float(row.get("open", 0.0) or 0.0),
						high=float(row.get("high", 0.0) or 0.0),
						low=float(row.get("low", 0.0) or 0.0),
						close=float(row.get("close", 0.0) or 0.0),
						adj_close=float(row.get("close", 0.0) or 0.0),
						volume=int(float(row.get("volume", 0) or 0)),
					)
				)
		except Exception:
			continue
	return all_bars


def upsert_prices(bars: List[PriceBar]) -> int:
	if not bars:
		return 0
	_init_prices_db()
	with _db(_PRICES_DB_PATH) as conn:
		conn.executemany(
			"""
			INSERT INTO prices(symbol, date, open, high, low, close, adj_close, volume)
			VALUES(?,?,?,?,?,?,?,?)
			ON CONFLICT(symbol, date) DO UPDATE SET
				open=excluded.open,
				high=excluded.high,
				low=excluded.low,
				close=excluded.close,
				adj_close=excluded.adj_close,
				volume=excluded.volume
			""",
			[
				(
					b.symbol,
					b.date,
					b.open,
					b.high,
					b.low,
					b.close,
					b.adj_close,
					b.volume,
				)
				for b in bars
			],
		)
		return conn.total_changes


def fetch_fundamentals(symbol: str) -> Dict[str, Any]:
	# Prefer Finnhub fundamentals (profile + metrics)
	if isinstance(_providers_cfg, dict) and (_providers_cfg.get("finnhub", {}) or {}).get("enabled", True):
		api_key = ((_providers_cfg.get("finnhub", {}) or {}).get("api_key") or os.getenv("FINNHUB_API_KEY", ""))
		profile = {}
		try:
			resp = requests.get("https://finnhub.io/api/v1/stock/profile2", params={"symbol": symbol, "token": api_key}, timeout=20)
			resp.raise_for_status()
			profile = resp.json() or {}
		except Exception:
			profile = {}
		metrics = {}
		try:
			resp = requests.get("https://finnhub.io/api/v1/stock/metric", params={"symbol": symbol, "metric": "all", "token": api_key}, timeout=20)
			resp.raise_for_status()
			metrics = (resp.json() or {}).get("metric", {}) or {}
		except Exception:
			metrics = {}
		mapped = {
			"market_cap": _safe_float(profile.get("marketCapitalization")) or _safe_float(metrics.get("marketCapitalization")),
			"trailing_pe": _safe_float(metrics.get("peBasicExclExtraTTM")) or _safe_float(metrics.get("peTTM")),
			"forward_pe": _safe_float(metrics.get("peBasicExclExtraAnnual")) or _safe_float(metrics.get("peForwardAnnual")),
			"shares": _safe_float(profile.get("shareOutstanding")),
			"name": profile.get("name"),
			"sector": profile.get("finnhubIndustry"),
		}
		return {k: v for k, v in mapped.items() if v is not None}
	# Fallback: minimal fundamentals via Twelve Data (quote only)
	api_key = ((_providers_cfg.get("twelvedata", {}) or {}).get("api_key") or os.getenv("TWELVEDATA_API_KEY", ""))
	try:
		resp = requests.get("https://api.twelvedata.com/quote", params={"symbol": symbol, "apikey": api_key}, timeout=20)
		resp.raise_for_status()
		q = resp.json() or {}
		mapped = {
			"market_cap": _safe_float(q.get("market_cap")),
			"name": q.get("name"),
		}
		return {k: v for k, v in mapped.items() if v is not None}
	except Exception:
		return {}


def _safe_int(x: Any) -> Optional[int]:
	try:
		return int(float(x))
	except Exception:
		return None


def _safe_float(x: Any) -> Optional[float]:
	try:
		return float(x)
	except Exception:
		return None


def _coerce_value(value: Any) -> Any:
	if value is None:
		return None
	try:
		number = _safe_float(value)
	except Exception:
		number = None
	if number is None:
		return value
	return int(number) if float(number).is_integer() else float(number)


def upsert_fundamentals(symbol: str, fundamentals: Dict[str, Any]) -> int:
	if not fundamentals:
		return 0
	_init_prices_db()
	as_of = _utcnow_iso()
	items = [(symbol, k, str(v), as_of) for k, v in fundamentals.items()]
	with _db(_PRICES_DB_PATH) as conn:
		conn.executemany(
			"""
			INSERT INTO fundamentals(symbol, key, value, as_of)
			VALUES(?,?,?,?)
			ON CONFLICT(symbol, key) DO UPDATE SET
				value=excluded.value,
				as_of=excluded.as_of
			""",
			items,
		)
		return conn.total_changes


def fetch_news_rss(feeds: Optional[List[str]] = None, symbols: Optional[List[str]] = None) -> List[Dict[str, Any]]:
	feeds = feeds or [
		"https://feeds.finance.yahoo.com/rss/2.0/headline?s=AAPL,MSFT,GOOG,AMZN&region=US&lang=en-US",
		"https://www.nasdaq.com/feed/rssoutbound?category=Stock%20Market%20News",
	]
	entries: List[Dict[str, Any]] = []
	for url in feeds:
		try:
			parsed = feedparser.parse(url)
			for e in parsed.entries:
				title = e.get("title")
				link = e.get("link")
				published = e.get("published") or e.get("updated")
				summary = e.get("summary")
				source = parsed.feed.get("title") if hasattr(parsed, "feed") else None
				if not title or not link:
					continue
				entries.append({
					"symbol": None,
					"title": title.strip(),
					"url": link.strip(),
					"published": published,
					"summary": summary,
					"source": source,
				})
		except Exception:
			continue
	# Optionally attempt naive symbol tagging
	if symbols:
		upper = set(s.upper() for s in symbols)
		for e in entries:
			text = f"{e.get('title','')} {e.get('summary','')}".upper()
			for s in upper:
				if f" {s} " in f" {text} ":
					e["symbol"] = s
	return entries


def upsert_news(entries: List[Dict[str, Any]]) -> int:
	if not entries:
		return 0
	_init_news_db()
	rows = [
		(
			e.get("symbol"),
			e.get("title"),
			e.get("url"),
			e.get("published"),
			e.get("summary"),
			e.get("source"),
		)
		for e in entries
	]
	with _db(_NEWS_DB_PATH) as conn:
		conn.executemany(
			"""
			INSERT INTO news(symbol, title, url, published, summary, source)
			VALUES(?,?,?,?,?,?)
			ON CONFLICT(url) DO UPDATE SET
				title=excluded.title,
				published=excluded.published,
				summary=excluded.summary,
				source=excluded.source
			""",
			rows,
		)
		return conn.total_changes


def get_latest_prices(symbol: str, limit: int = 30) -> List[Dict[str, Any]]:
	_init_prices_db()
	with _db(_PRICES_DB_PATH) as conn:
		cur = conn.execute(
			"SELECT date, open, high, low, close, adj_close, volume FROM prices WHERE symbol=? ORDER BY date DESC LIMIT ?",
			(symbol, limit),
		)
		cols = [d[0] for d in cur.description]
		return [dict(zip(cols, row)) for row in cur.fetchall()]


def get_latest_news(limit: int = 50) -> List[Dict[str, Any]]:
	_init_news_db()
	with _db(_NEWS_DB_PATH) as conn:
		cur = conn.execute(
			"SELECT symbol, title, url, published, summary, source FROM news ORDER BY id DESC LIMIT ?",
			(limit,),
		)
		cols = [d[0] for d in cur.description]
		return [dict(zip(cols, row)) for row in cur.fetchall()]


def get_fundamentals(symbols: Optional[List[str]] = None) -> Dict[str, Dict[str, Any]]:
	"""
	Return the latest fundamental key/value snapshot for the requested symbols.

	Values are coerced into floats/ints when possible so downstream consumers can
	easily compute ratios without additional parsing.
	"""
	_init_prices_db()
	query = "SELECT symbol, key, value, as_of FROM fundamentals"
	params: Tuple[Any, ...] = ()
	if symbols:
		placeholders = ",".join("?" for _ in symbols)
		query += f" WHERE symbol IN ({placeholders})"
		params = tuple(s.upper().strip() for s in symbols)
	query += " ORDER BY symbol ASC"

	results: Dict[str, Dict[str, Any]] = {}
	with _db(_PRICES_DB_PATH) as conn:
		cur = conn.execute(query, params)
		for symbol, key, value, as_of in cur.fetchall():
			if not symbol or not key:
				continue
			symbol = symbol.upper().strip()
			entry = results.setdefault(symbol, {"as_of": as_of})
			entry[key] = _coerce_value(value)
	return results


__all__ = [
	"fetch_prices",
	"upsert_prices",
	"fetch_fundamentals",
	"upsert_fundamentals",
	"fetch_news_rss",
	"upsert_news",
	"get_latest_prices",
	"get_latest_news",
	"get_fundamentals",
]
