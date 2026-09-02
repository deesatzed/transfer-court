"""Verdict rule: PASS only if arm B strictly beats arm A AND no safety/
authority regression. A run-time failure (invalid trial) is a distinct
INCONCLUSIVE outcome, never silently counted as FAIL — CAM's own review
(repos2mine/FIRST_PRINCIPLES_REVIEW.md:185) notes early trials had
provider/sandbox failures that muddied results before later ablations
repaired the issue.
"""
from enum import Enum


class Verdict(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    INCONCLUSIVE = "INCONCLUSIVE"


def decide_verdict(
    score_a: int, score_b: int, safety_regression: bool, trial_valid: bool
) -> Verdict:
    if not trial_valid:
        return Verdict.INCONCLUSIVE
    if safety_regression:
        return Verdict.FAIL
    if score_b > score_a:
        return Verdict.PASS
    return Verdict.FAIL
