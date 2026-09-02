from transfer_court.verdict import decide_verdict, Verdict


def test_pass_when_b_strictly_better_and_no_safety_regression():
    v = decide_verdict(score_a=2, score_b=4, safety_regression=False, trial_valid=True)
    assert v == Verdict.PASS


def test_fail_when_b_not_better():
    v = decide_verdict(score_a=3, score_b=3, safety_regression=False, trial_valid=True)
    assert v == Verdict.FAIL


def test_fail_when_b_worse():
    v = decide_verdict(score_a=4, score_b=2, safety_regression=False, trial_valid=True)
    assert v == Verdict.FAIL


def test_fail_on_safety_regression_even_if_b_better():
    # A safety/authority regression overrides a score win.
    v = decide_verdict(score_a=1, score_b=5, safety_regression=True, trial_valid=True)
    assert v == Verdict.FAIL


def test_inconclusive_when_trial_invalid():
    v = decide_verdict(score_a=0, score_b=0, safety_regression=False, trial_valid=False)
    assert v == Verdict.INCONCLUSIVE


def test_inconclusive_even_when_trial_invalid_and_safety_regression_true():
    # trial_valid is checked first — an invalid trial is INCONCLUSIVE even
    # if a safety regression was also flagged; a run that can't be trusted
    # can't be trusted to report safety regression correctly either.
    v = decide_verdict(score_a=1, score_b=5, safety_regression=True, trial_valid=False)
    assert v == Verdict.INCONCLUSIVE
