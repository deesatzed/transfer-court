from pathlib import Path
from unittest.mock import MagicMock

from transfer_court.trial import run_paired_trial
from transfer_court.docket import DocketItem
from transfer_court.panel import Panel
from transfer_court.sandbox import SandboxResult


def _docket_item():
    panel = Panel(
        capability="c", applicability=["a"], evidence=["e"], actions=["ac"],
        seams=["s"], proofs=["p"], risks=["r"], hardening="draft",
    )
    return DocketItem(
        panel=panel, source_repo="/x", source_commit="abc1234",
        target_repo="/y", target_commit="def5678", obligation="do the thing",
    )


def test_run_paired_trial_calls_builder_twice_with_and_without_panel():
    builder = MagicMock(side_effect=[
        SandboxResult(returncode=0, stdout="arm A output", stderr=""),
        SandboxResult(returncode=0, stdout="arm B output", stderr=""),
    ])
    item = _docket_item()

    result = run_paired_trial(item, builder=builder)

    assert builder.call_count == 2
    call_a_kwargs = builder.call_args_list[0].kwargs
    call_b_kwargs = builder.call_args_list[1].kwargs
    assert call_a_kwargs["panel"] is None
    assert call_b_kwargs["panel"] == item.panel
    assert result.arm_a_output == "arm A output"
    assert result.arm_b_output == "arm B output"


def test_run_paired_trial_marks_invalid_on_sandbox_failure():
    builder = MagicMock(side_effect=[
        SandboxResult(returncode=1, stdout="", stderr="crashed"),
        SandboxResult(returncode=0, stdout="arm B output", stderr=""),
    ])
    result = run_paired_trial(_docket_item(), builder=builder)
    assert result.valid is False
    assert "arm A" in result.invalid_reason


def test_run_paired_trial_skips_arm_b_when_arm_a_fails():
    # Arm B represents a real, potentially minutes-long sandboxed attempt —
    # it should never run once the trial is already invalid from arm A.
    builder = MagicMock(return_value=SandboxResult(returncode=1, stdout="", stderr="crashed"))
    result = run_paired_trial(_docket_item(), builder=builder)
    assert builder.call_count == 1
    assert result.arm_b_output == ""
