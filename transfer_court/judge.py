"""Frozen judge: scores one arm's output against the docket obligation,
0-5, with no knowledge of which arm (A or B) produced the output and no
visibility into the Panel ("no hindsight leakage" — the judge is blind to
which arm produced the output it's scoring).

Pattern adapted from a sibling project's memory-adoption judge
(JSON-terminated response, regex extraction, retry-with-backoff). Rubric
content is new — obligation-success scoring, not ideology-adoption scoring.
"""
import json
import os
import re
import time

import anthropic

# Model is env-configurable, not hardcoded: current model IDs shift, and the
# caller/user is the source of truth for which model to run the judge on.
JUDGE_MODEL = os.environ.get("TRANSFER_COURT_JUDGE_MODEL", "claude-sonnet-5")

# Only these are worth retrying: transient network/service conditions. A 4xx
# (bad model ID, auth failure, bad request) will fail identically on every
# retry and should surface immediately, not burn 3 attempts to reach the
# same fabricated score-0 result decide_verdict can't tell apart from a
# genuinely bad output (see JudgeError below).
_RETRYABLE_EXCEPTIONS = (
    anthropic.APIConnectionError,
    anthropic.RateLimitError,
    anthropic.InternalServerError,
)


class JudgeError(RuntimeError):
    """Raised when the judge cannot produce a score at all (retries
    exhausted, or a non-retryable API/response-shape error). A judge failure
    must never silently collapse to score 0 — decide_verdict has no way to
    distinguish a fabricated 0 from a real one, and a broken judge would
    otherwise make every trial FAIL without any visible signal that the
    judge itself, not the Panel, is what's broken."""


def judge_output(obligation: str, output: str) -> tuple[int, str]:
    """Score `output` 0-5 against `obligation`, blind to arm/Panel identity.

    Returns (score, raw_judge_response) on success.
    Raises JudgeError if the judge cannot produce a score.
    """
    if not output or not output.strip():
        return 0, "(empty output — nothing to judge)"

    prompt = (
        f"An engineer was given this obligation:\n\n{obligation}\n\n"
        f"They produced this output:\n\n---BEGIN OUTPUT---\n{output}\n"
        f"---END OUTPUT---\n\n"
        "Score how well the output satisfies the obligation, 0-5:\n"
        "0 = does not address the obligation at all\n"
        "1 = addresses it but fundamentally broken or off-target\n"
        "2 = partial, with a significant gap or defect\n"
        "3 = mostly correct, minor gaps\n"
        "4 = fully correct, satisfies the obligation cleanly\n"
        "5 = fully correct and demonstrates additional robustness beyond the "
        "literal obligation\n\n"
        "Respond with brief reasoning (2-3 sentences) then ONLY valid JSON on "
        'the last line: {"score": N}'
    )

    client = anthropic.Anthropic()
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            resp = client.messages.create(
                model=JUDGE_MODEL,
                system=(
                    "You are a strict, impartial judge. You do not know how "
                    "many candidate outputs exist or how they were produced. "
                    "Score only what is in front of you."
                ),
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300,
            )
            raw = resp.content[0].text
            return extract_score(raw), raw
        except _RETRYABLE_EXCEPTIONS as e:
            last_error = e
            if attempt < 2:
                time.sleep(2 ** attempt)
        except Exception as e:
            # Not retryable: a bad model ID, auth failure, or an unexpected
            # response shape (e.g. resp.content[0] missing/not text) will
            # fail the same way every time. Surface it immediately instead
            # of masking it as three identical transient-looking retries.
            raise JudgeError(f"judge call failed: {e}") from e

    raise JudgeError(f"judge failed after 3 attempts: {last_error}")


def extract_score(text: str) -> int:
    matches = list(re.finditer(r"\{[^}]+\}", text, re.DOTALL))
    for match in reversed(matches):
        try:
            parsed = json.loads(match.group())
            if "score" in parsed:
                return max(0, min(5, int(parsed["score"])))
        except (json.JSONDecodeError, ValueError, TypeError):
            continue
    m = re.search(r'"score"\s*:\s*(\d)', text)
    if m:
        return max(0, min(5, int(m.group(1))))
    return 0
