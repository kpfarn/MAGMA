from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

import feedparser
import pandas as pd
import yfinance as yf

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
	data = yf.download(" ".join(symbols), period=period, interval=interval, group_by="ticker", auto_adjust=False, progress=False)
	bars: List[PriceBar] = []
	if isinstance(data.columns, pd.MultiIndex):
		for symbol in symbols:
			if symbol not in data.columns.levels[0]:
				continue
			df = data[symbol].reset_index()
			for _, row in df.iterrows():
				bars.append(
					PriceBar(
						symbol=symbol,
						date=row["Date"].strftime("%Y-%m-%d"),
						open=float(row.get("Open", float("nan")) or 0.0),
						high=float(row.get("High", float("nan")) or 0.0),
						low=float(row.get("Low", float("nan")) or 0.0),
						close=float(row.get("Close", float("nan")) or 0.0),
						adj_close=float(row.get("Adj Close", float("nan")) or 0.0),
						volume=int(row.get("Volume", 0) or 0),
					)
				)
	else:
		# Single symbol case
		df = data.reset_index()
		for _, row in df.iterrows():
			bars.append(
				PriceBar(
					symbol=symbols[0],
					date=row["Date"].strftime("%Y-%m-%d"),
					open=float(row.get("Open", float("nan")) or 0.0),
					high=float(row.get("High", float("nan")) or 0.0),
					low=float(row.get("Low", float("nan")) or 0.0),
					close=float(row.get("Close", float("nan")) or 0.0),
					adj_close=float(row.get("Adj Close", float("nan")) or 0.0),
					volume=int(row.get("Volume", 0) or 0),
				)
			)
	return bars


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
	t = yf.Ticker(symbol)
	info = t.get_info() or {}
	fast_info = getattr(t, "fast_info", None)
	funds: Dict[str, Any] = {**info}
	if fast_info:
		try:
			funds.update({
				"market_cap": getattr(fast_info, "market_cap", None),
				"trailing_pe": getattr(fast_info, "trailing_pe", None),
				"forward_pe": getattr(fast_info, "forward_pe", None),
				"shares": getattr(fast_info, "shares", None),
			})
		except Exception:
			pass
	return funds


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


__all__ = [
	"fetch_prices",
	"upsert_prices",
	"fetch_fundamentals",
	"upsert_fundamentals",
	"fetch_news_rss",
	"upsert_news",
	"get_latest_prices",
	"get_latest_news",
]
