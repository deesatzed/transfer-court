"""Append-only receipts: a verdict is never edited, only superseded by a
new trial's receipt.
"""
import json
import os
from pathlib import Path
from typing import Any

# Every receipt must carry these — a receipt missing one would write
# successfully (valid JSON, correct docket_id) and only fail much later
# when CAM_Codx tries to read a field that was never there.
REQUIRED_FIELDS = frozenset({
    "docket_id", "verdict", "score_a", "score_b",
    "arm_a_output", "arm_b_output", "judge_raw_a", "judge_raw_b",
    "source_commit", "target_commit",
})


class ReceiptExistsError(Exception):
    pass


def write_receipt(data: dict[str, Any], receipts_dir: Path) -> Path:
    missing = REQUIRED_FIELDS - data.keys()
    if missing:
        raise ValueError(f"receipt data is missing required fields: {sorted(missing)}")

    receipts_dir = Path(receipts_dir)
    receipts_dir.mkdir(parents=True, exist_ok=True)
    docket_id = data["docket_id"]
    path = receipts_dir / f"{docket_id}.json"

    verdict = data["verdict"]
    serializable = {
        **data,
        "verdict": verdict.value if hasattr(verdict, "value") else verdict,
    }
    payload = json.dumps(serializable, indent=2, sort_keys=True)

    # O_CREAT | O_EXCL makes the existence-check-and-write atomic at the OS
    # level, closing the TOCTOU gap a separate path.exists() check would
    # leave between checking and writing — receipts must never be silently
    # clobbered by a concurrent write for the same docket_id.
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        raise ReceiptExistsError(
            f"receipt for docket {docket_id} already exists at {path}; "
            "receipts are append-only, re-run with a new docket_id"
        ) from None
    with os.fdopen(fd, "w") as f:
        f.write(payload)
    return path
