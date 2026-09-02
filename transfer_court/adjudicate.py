"""Top-level entry point: wires Panel/DocketItem -> paired trial -> blind
judge (both arms) -> verdict -> receipt. This is the whole pipeline from
the design doc's architecture diagram, minus the mining (CAM) and the
promotion decision (also CAM, external, reads the receipt this emits).
"""
from dataclasses import dataclass
from pathlib import Path

from transfer_court.docket import DocketItem
from transfer_court.judge import JudgeError, judge_output
from transfer_court.receipt import write_receipt
from transfer_court.trial import BuilderFn, run_paired_trial
from transfer_court.verdict import Verdict, decide_verdict


@dataclass
class AdjudicationResult:
    verdict: Verdict
    score_a: int
    score_b: int
    receipt_path: Path


def adjudicate(
    item: DocketItem,
    docket_id: str,
    builder: BuilderFn,
    safety_regression: bool,
    receipts_dir: Path,
) -> AdjudicationResult:
    trial = run_paired_trial(item, builder=builder)

    if not trial.valid:
        verdict = decide_verdict(score_a=0, score_b=0, safety_regression=False, trial_valid=False)
        score_a, score_b = 0, 0
        judge_raw_a, judge_raw_b = trial.invalid_reason, trial.invalid_reason
    else:
        # judge_output can raise JudgeError (Task 6) if the judge itself
        # fails (bad model config, non-retryable API error, retries
        # exhausted) -- this must NOT crash adjudicate() uncaught, and it
        # must NOT be allowed to silently look like a real score. A judge
        # failure makes the trial's *outcome* untrustworthy the same way a
        # sandbox failure does, so it takes the same INCONCLUSIVE path
        # trial.valid=False already takes, with the JudgeError's message
        # standing in for invalid_reason.
        try:
            score_a, judge_raw_a = judge_output(item.obligation, trial.arm_a_output)
            score_b, judge_raw_b = judge_output(item.obligation, trial.arm_b_output)
            verdict = decide_verdict(
                score_a=score_a, score_b=score_b,
                safety_regression=safety_regression, trial_valid=True,
            )
        except JudgeError as e:
            verdict = decide_verdict(score_a=0, score_b=0, safety_regression=False, trial_valid=False)
            score_a, score_b = 0, 0
            judge_raw_a = judge_raw_b = f"judge failed: {e}"

    receipt_path = write_receipt(
        {
            "docket_id": docket_id,
            "verdict": verdict,
            "score_a": score_a,
            "score_b": score_b,
            "arm_a_output": trial.arm_a_output,
            "arm_b_output": trial.arm_b_output,
            "judge_raw_a": judge_raw_a,
            "judge_raw_b": judge_raw_b,
            "source_commit": item.source_commit,
            "target_commit": item.target_commit,
        },
        receipts_dir=receipts_dir,
    )

    return AdjudicationResult(
        verdict=verdict, score_a=score_a, score_b=score_b, receipt_path=receipt_path,
    )
