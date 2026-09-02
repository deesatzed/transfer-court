"""Two-arm paired trial: arm A (target + obligation only) vs. arm B (target +
obligation + Panel). Same builder callable, same task, same time budget for
both arms.
"""
from dataclasses import dataclass
from typing import Callable, Optional

from transfer_court.docket import DocketItem
from transfer_court.sandbox import SandboxResult

BuilderFn = Callable[..., SandboxResult]


@dataclass
class PairedTrialResult:
    arm_a_output: str
    arm_b_output: str
    valid: bool
    invalid_reason: Optional[str] = None


def run_paired_trial(item: DocketItem, builder: BuilderFn) -> PairedTrialResult:
    # Arm B is only run if arm A succeeds: builder is expected to represent a
    # real sandboxed attempt (potentially minutes-long, timeout-bound), so
    # there is no reason to pay that cost for an arm whose result would be
    # discarded anyway once the trial is already invalid.
    arm_a = builder(docket_item=item, panel=None)
    if arm_a.returncode != 0:
        return PairedTrialResult(
            arm_a_output=arm_a.stdout, arm_b_output="",
            valid=False, invalid_reason=f"arm A sandbox failed: {arm_a.stderr[:200]}",
        )

    arm_b = builder(docket_item=item, panel=item.panel)
    if arm_b.returncode != 0:
        return PairedTrialResult(
            arm_a_output=arm_a.stdout, arm_b_output=arm_b.stdout,
            valid=False, invalid_reason=f"arm B sandbox failed: {arm_b.stderr[:200]}",
        )

    return PairedTrialResult(
        arm_a_output=arm_a.stdout, arm_b_output=arm_b.stdout, valid=True,
    )
