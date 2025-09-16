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


def get_portfolio_data() -> Dict[str, Any]:
	"""Return holdings with computed PnL using latest close from prices table."""
	_init()
	with _db() as conn:
		cur = conn.execute("SELECT ticker, shares, avg_cost FROM holdings ORDER BY ticker ASC")
		rows = cur.fetchall()
		holdings: List[Dict[str, Any]] = []
		total_value = 0.0
		for ticker, shares, avg_cost in rows:
			last = _latest_close_for(conn, ticker) or 0.0
			market_value = float(shares) * float(last)
			cost_basis = float(shares) * float(avg_cost)
			pnl = market_value - cost_basis
			holdings.append({
				"ticker": ticker,
				"shares": float(shares),
				"avg_cost": float(avg_cost),
				"last": float(last),
				"pnl": float(pnl),
			})
			total_value += market_value
		return {"holdings": holdings, "total_value": float(total_value)}


__all__ = [
	"upsert_holding",
	"record_transaction",
	"get_portfolio_data",
]


