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
    arm_a = builder(docket_item=item, panel=None)
    arm_b = builder(docket_item=item, panel=item.panel)

    if arm_a.returncode != 0:
        return PairedTrialResult(
            arm_a_output=arm_a.stdout, arm_b_output=arm_b.stdout,
            valid=False, invalid_reason=f"arm A sandbox failed: {arm_a.stderr[:200]}",
        )
    if arm_b.returncode != 0:
        return PairedTrialResult(
            arm_a_output=arm_a.stdout, arm_b_output=arm_b.stdout,
            valid=False, invalid_reason=f"arm B sandbox failed: {arm_b.stderr[:200]}",
        )

    return PairedTrialResult(
        arm_a_output=arm_a.stdout, arm_b_output=arm_b.stdout, valid=True,
    )
