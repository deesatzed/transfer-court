"""Append-only receipts: a verdict is never edited, only superseded by a
new trial's receipt.
"""
import json
from pathlib import Path
from typing import Any


class ReceiptExistsError(Exception):
    pass


def write_receipt(data: dict[str, Any], receipts_dir: Path) -> Path:
    receipts_dir = Path(receipts_dir)
    receipts_dir.mkdir(parents=True, exist_ok=True)
    docket_id = data["docket_id"]
    path = receipts_dir / f"{docket_id}.json"
    if path.exists():
        raise ReceiptExistsError(
            f"receipt for docket {docket_id} already exists at {path}; "
            "receipts are append-only, re-run with a new docket_id"
        )
    verdict = data["verdict"]
    serializable = {
        **data,
        "verdict": verdict.value if hasattr(verdict, "value") else verdict,
    }
    path.write_text(json.dumps(serializable, indent=2, sort_keys=True))
    return path
