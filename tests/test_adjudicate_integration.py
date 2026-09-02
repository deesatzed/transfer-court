import json
from unittest.mock import patch

from transfer_court.adjudicate import adjudicate
from transfer_court.docket import DocketItem
from transfer_court.judge import JudgeError
from transfer_court.panel import Panel
from transfer_court.sandbox import SandboxResult
from transfer_court.verdict import Verdict


def _synthetic_docket_item():
    panel = Panel(
        capability="round numbers to 2 decimal places before display",
        applicability=["output is a floating point currency value"],
        evidence=["synthetic test fixture, not a real mined Panel"],
        actions=["wrap value in round(x, 2)"],
        seams=["display formatting function"],
        proofs=["output matches expected string"],
        risks=["none — synthetic fixture"],
        hardening="draft",
    )
    return DocketItem(
        panel=panel,
        source_repo="/synthetic/source",
        source_commit="0000000",
        target_repo="/synthetic/target",
        target_commit="1111111",
        obligation="format 19.999 as currency with exactly 2 decimal places",
    )


@patch("transfer_court.adjudicate.judge_output")
def test_adjudicate_produces_pass_verdict_and_receipt(mock_judge, tmp_path):
    # Arm A (no panel) does it wrong, arm B (with panel) does it right.
    mock_judge.side_effect = [
        (1, "arm A: wrong, e.g. '19.999'"),
        (5, "arm B: correct, '$20.00'"),
    ]

    def fake_builder(docket_item, panel):
        if panel is None:
            return SandboxResult(returncode=0, stdout="19.999", stderr="")
        return SandboxResult(returncode=0, stdout="$20.00", stderr="")

    item = _synthetic_docket_item()
    result = adjudicate(
        item, docket_id="synthetic-001", builder=fake_builder,
        safety_regression=False, receipts_dir=tmp_path,
    )

    assert result.verdict == Verdict.PASS
    assert (tmp_path / "synthetic-001.json").exists()


@patch("transfer_court.adjudicate.judge_output")
def test_adjudicate_handles_judge_error_as_inconclusive(mock_judge, tmp_path):
    mock_judge.side_effect = JudgeError("boom")

    def fake_builder(docket_item, panel):
        if panel is None:
            return SandboxResult(returncode=0, stdout="19.999", stderr="")
        return SandboxResult(returncode=0, stdout="$20.00", stderr="")

    item = _synthetic_docket_item()
    result = adjudicate(
        item, docket_id="synthetic-002", builder=fake_builder,
        safety_regression=False, receipts_dir=tmp_path,
    )

    assert result.verdict == Verdict.INCONCLUSIVE

    receipt_path = tmp_path / "synthetic-002.json"
    assert receipt_path.exists()

    receipt = json.loads(receipt_path.read_text())
    assert "boom" in receipt["judge_raw_a"]
    assert "boom" in receipt["judge_raw_b"]


@patch("transfer_court.adjudicate.judge_output")
def test_adjudicate_preserves_real_score_when_only_one_arm_judge_fails(mock_judge, tmp_path):
    # Arm A judges successfully; only arm B's judge_output call fails.
    # Arm A's real score/judge_raw must survive into the receipt rather
    # than being overwritten by arm B's failure.
    mock_judge.side_effect = [
        (4, "arm A judged fine, score 4"),
        JudgeError("arm B boom"),
    ]

    def fake_builder(docket_item, panel):
        if panel is None:
            return SandboxResult(returncode=0, stdout="19.999", stderr="")
        return SandboxResult(returncode=0, stdout="$20.00", stderr="")

    item = _synthetic_docket_item()
    result = adjudicate(
        item, docket_id="synthetic-003", builder=fake_builder,
        safety_regression=False, receipts_dir=tmp_path,
    )

    assert result.verdict == Verdict.INCONCLUSIVE

    receipt = json.loads((tmp_path / "synthetic-003.json").read_text())
    assert receipt["judge_raw_a"] == "arm A judged fine, score 4"
    assert "arm B boom" in receipt["judge_raw_b"]
    assert "arm A" not in receipt["judge_raw_b"]
