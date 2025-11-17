from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple


_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DB_PATH = os.path.join(_BASE_DIR, "data", "portfolio.db")
os.makedirs(os.path.dirname(_DB_PATH), exist_ok=True)

try:
	from . import formulas  # type: ignore
except Exception:
	formulas = None


@contextmanager
def _db() -> Iterable[sqlite3.Connection]:
	conn = sqlite3.connect(_DB_PATH)
	try:
		conn.execute("PRAGMA journal_mode=WAL;")
		conn.execute("PRAGMA synchronous=NORMAL;")
		yield conn
		conn.commit()
	finally:
		conn.close()


def _init() -> None:
	with _db() as conn:
		conn.execute(
			"""
			CREATE TABLE IF NOT EXISTS holdings (
				id INTEGER PRIMARY KEY AUTOINCREMENT,
				ticker TEXT NOT NULL,
				shares REAL NOT NULL,
				avg_cost REAL NOT NULL,
				updated_at TEXT NOT NULL,
				UNIQUE(ticker)
			);
			"""
		)
		conn.execute(
			"""
			CREATE TABLE IF NOT EXISTS transactions (
				id INTEGER PRIMARY KEY AUTOINCREMENT,
				ticker TEXT NOT NULL,
				action TEXT NOT NULL,
				shares REAL NOT NULL,
				price REAL NOT NULL,
				at TEXT NOT NULL
			);
			"""
		)


def _utcnow_iso() -> str:
	return datetime.now(timezone.utc).isoformat()


def upsert_holding(ticker: str, shares: float, avg_cost: float) -> int:
	"""Create or update a holding. If shares=0, remove it."""
	_init()
	ticker = ticker.upper().strip()
	with _db() as conn:
		if shares == 0:
			cur = conn.execute("DELETE FROM holdings WHERE ticker=?", (ticker,))
			return cur.rowcount
		conn.execute(
			"""
			INSERT INTO holdings(ticker, shares, avg_cost, updated_at)
			VALUES(?,?,?,?)
			ON CONFLICT(ticker) DO UPDATE SET
				shares=excluded.shares,
				avg_cost=excluded.avg_cost,
				updated_at=excluded.updated_at
			""",
			(ticker, float(shares), float(avg_cost), _utcnow_iso()),
		)
		return conn.total_changes


def record_transaction(ticker: str, action: str, shares: float, price: float) -> int:
	"""Record a buy/sell transaction. Does not mutate holdings automatically."""
	_init()
	action = action.lower().strip()
	if action not in {"buy", "sell"}:
		raise ValueError("action must be 'buy' or 'sell'")
	with _db() as conn:
		conn.execute(
			"INSERT INTO transactions(ticker, action, shares, price, at) VALUES(?,?,?,?,?)",
			(ticker.upper().strip(), action, float(shares), float(price), _utcnow_iso()),
		)
		return conn.total_changes


def _latest_close_for(conn: sqlite3.Connection, ticker: str) -> Optional[float]:
	cur = conn.execute(
		"SELECT close FROM prices WHERE symbol=? ORDER BY date DESC LIMIT 1",
		(ticker.upper().strip(),),
	)
	row = cur.fetchone()
	return float(row[0]) if row and row[0] is not None else None


def _fetch_fundamentals_for(conn: sqlite3.Connection, tickers: List[str]) -> Dict[str, Dict[str, Any]]:
	if not tickers:
		return {}
	placeholders = ",".join("?" for _ in tickers)
	cur = conn.execute(
		f"SELECT symbol, key, value, as_of FROM fundamentals WHERE symbol IN ({placeholders})",
		[t.upper().strip() for t in tickers],
	)
	fundamentals: Dict[str, Dict[str, Any]] = {}
	for symbol, key, value, as_of in cur.fetchall():
		if not symbol or not key:
			continue
		entry = fundamentals.setdefault(symbol, {"as_of": as_of})
		entry[key] = _coerce_numeric(value)
	return fundamentals


def _coerce_numeric(value: Any) -> Any:
	if value is None:
		return None
	try:
		if "." in str(value):
			return float(value)
		return int(value)
	except Exception:
		try:
			return float(value)
		except Exception:
			return value


def _clamp_score(value: float, lower: float = 0.0, upper: float = 10.0) -> float:
	return max(lower, min(upper, value))


def _run_formula(payload: Dict[str, Any]) -> Optional[float]:
	if not formulas or not hasattr(formulas, "apply_formula"):
		return None
	try:
		raw = formulas.apply_formula(payload)
	except NotImplementedError:
		return None
	except Exception:
		return None
	if raw is None:
		return None
	try:
		return _clamp_score(float(raw))
	except Exception:
		return None


def get_portfolio_data() -> Dict[str, Any]:
	"""Return holdings enriched with fundamentals, allocation stats, and health score."""
	_init()
	with _db() as conn:
		cur = conn.execute("SELECT ticker, shares, avg_cost FROM holdings ORDER BY ticker ASC")
		rows = cur.fetchall()
		tickers = [r[0] for r in rows]
		fundamentals_map = _fetch_fundamentals_for(conn, tickers)

		holdings: List[Dict[str, Any]] = []
		total_value = 0.0
		total_cost = 0.0
		for ticker, shares, avg_cost in rows:
			last = _latest_close_for(conn, ticker) or 0.0
			shares = float(shares)
			avg_cost = float(avg_cost)
			market_value = shares * float(last)
			cost_basis = shares * avg_cost
			pnl = market_value - cost_basis
			pnl_pct = (pnl / cost_basis) * 100 if cost_basis else 0.0
			total_value += market_value
			total_cost += cost_basis
			holdings.append({
				"ticker": ticker,
				"shares": shares,
				"avg_cost": avg_cost,
				"last": float(last),
				"market_value": market_value,
				"cost_basis": cost_basis,
				"pnl": pnl,
				"pnl_pct": pnl_pct,
				"fundamentals": fundamentals_map.get(ticker.upper().strip(), {}),
				"weight": 0.0,  # populated after totals calculated
			})

		if total_value:
			for holding in holdings:
				holding["weight"] = holding["market_value"] / total_value

		sector_buckets: Dict[str, float] = {}
		for holding in holdings:
			sector = holding.get("fundamentals", {}).get("sector") or "Unclassified"
			sector_buckets[sector] = sector_buckets.get(sector, 0.0) + holding.get("market_value", 0.0)

		sector_exposure = []
		for sector, value in sorted(sector_buckets.items(), key=lambda x: x[1], reverse=True):
			sector_exposure.append({
				"sector": sector,
				"weight": (value / total_value) if total_value else 0.0,
				"value": value,
			})

		largest_positions = sorted(holdings, key=lambda h: h.get("market_value", 0.0), reverse=True)[:5]
		total_pnl = total_value - total_cost
		summary = {
			"total_value": total_value,
			"total_cost_basis": total_cost,
			"total_pnl": total_pnl,
			"pnl_pct": (total_pnl / total_cost) * 100 if total_cost else 0.0,
			"largest_positions": [
				{"ticker": h["ticker"], "weight": h["weight"], "market_value": h["market_value"], "pnl_pct": h["pnl_pct"]}
				for h in largest_positions
			],
			"sector_exposure": sector_exposure,
		}

		score = _run_formula({
			"summary": summary,
			"holdings": holdings,
		})
		if score is not None:
			summary["health_score"] = score

		return {"holdings": holdings, "summary": summary}


__all__ = [
	"upsert_holding",
	"record_transaction",
	"get_portfolio_data",
]


