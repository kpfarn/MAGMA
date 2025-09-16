from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

try:
	import yaml  # type: ignore
except Exception:
	yaml = None

from . import data_pipeline as dp
from . import llm_interface as llm


def _read_config() -> Dict[str, Any]:
	base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
	config_path = os.path.join(base_dir, "config.yaml")
	if yaml is None or not os.path.exists(config_path):
		return {}
	with open(config_path, "r", encoding="utf-8") as f:
		return yaml.safe_load(f) or {}


cfg = _read_config()
server_cfg = (cfg.get("server") or {})

app = FastAPI(title="MAGMA API", version="0.1.0")

# CORS for local dev frontend
app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)


@app.get("/health")
def health() -> Dict[str, str]:
	return {"status": "ok"}


@app.get("/news")
def get_news(limit: int = 50) -> Dict[str, Any]:
	items = dp.get_latest_news(limit=limit)
	# If empty, attempt to fetch and cache once
	if not items:
		entries = dp.fetch_news_rss(
			feeds=((cfg.get("providers", {}) or {}).get("news", {}) or {}).get("rss_feeds")
		)
		dp.upsert_news(entries)
		items = dp.get_latest_news(limit=limit)
	return {"news": items}


@app.get("/portfolio")
def get_portfolio() -> Dict[str, Any]:
	# Base implementation: return an empty portfolio placeholder
	# Frontend expects { holdings: [...] }
	return {"holdings": []}


def _gather_market_snapshot(symbols: Optional[List[str]] = None) -> Dict[str, Any]:
	# Pick a small default watchlist if no symbols provided
	symbols = symbols or ["AAPL", "MSFT", "GOOG", "AMZN"]
	prices = dp.fetch_prices(symbols=symbols, period="1mo", interval="1d")
	# Convert to dicts grouped by symbol
	buckets: Dict[str, List[Dict[str, Any]]] = {}
	for b in prices:
		buckets.setdefault(b.symbol, []).append({
			"date": b.date,
			"open": b.open,
			"high": b.high,
			"low": b.low,
			"close": b.close,
			"adj_close": b.adj_close,
			"volume": b.volume,
		})
	news = dp.get_latest_news(limit=50)
	return {"prices": buckets, "news": news}


@app.get("/recommendations")
def get_recommendations_endpoint() -> Dict[str, Any]:
	# In the base implementation, we use an empty portfolio with a default watchlist
	portfolio: Dict[str, Any] = {"holdings": []}
	data = _gather_market_snapshot()
	try:
		resp = llm.get_recommendations(data=data, portfolio=portfolio)
	except Exception as e:
		raise HTTPException(status_code=500, detail=f"LLM error: {e}")
	# Return a simple wrapper for the frontend. The frontend currently
	# expects { recommendations: [...] }. We provide the raw text for now.
	return {"model": resp.get("model"), "text": resp.get("text", ""), "recommendations": []}


if __name__ == "__main__":
	import uvicorn
	host = str(server_cfg.get("host", "0.0.0.0"))
	port = int(server_cfg.get("port", 8000))
	uvicorn.run("MAGMA.backend.app:app", host=host, port=port, reload=True)









































































