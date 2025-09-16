import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional


def _default_log_path() -> str:
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(base_dir, "data")
    os.makedirs(data_dir, exist_ok=True)
    return os.path.join(data_dir, "conversations.jsonl")


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def append_jsonl(record: Dict[str, Any], path: Optional[str] = None) -> None:
    log_path = path or _default_log_path()
    # Ensure parent directory exists
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    # Add timestamp if missing
    record = {**record}
    record.setdefault("timestamp", _utcnow_iso())
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


__all__ = ["append_jsonl"]


