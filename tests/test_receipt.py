import json
from pathlib import Path

import pytest

from transfer_court.receipt import write_receipt, ReceiptExistsError
from transfer_court.verdict import Verdict


def _sample_receipt_data():
    return {
        "docket_id": "test-001",
        "verdict": Verdict.PASS,
        "score_a": 2,
        "score_b": 4,
        "arm_a_output": "...",
        "arm_b_output": "...",
        "judge_raw_a": "...",
        "judge_raw_b": "...",
        "source_commit": "abc1234",
        "target_commit": "def5678",
    }


def test_write_receipt_creates_file(tmp_path):
    path = write_receipt(_sample_receipt_data(), receipts_dir=tmp_path)
    assert path.exists()
    data = json.loads(path.read_text())
    assert data["verdict"] == "PASS"
    assert data["docket_id"] == "test-001"


def test_write_receipt_refuses_to_overwrite(tmp_path):
    write_receipt(_sample_receipt_data(), receipts_dir=tmp_path)
    with pytest.raises(ReceiptExistsError):
        write_receipt(_sample_receipt_data(), receipts_dir=tmp_path)
