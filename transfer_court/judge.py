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


def judge_output(obligation: str, output: str) -> tuple[int, str]:
    """Score `output` 0-5 against `obligation`, blind to arm/Panel identity.

    Returns (score, raw_judge_response).
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
        except Exception as e:
            if attempt == 2:
                return 0, f"(judge error after 3 attempts: {str(e)[:200]})"
            time.sleep(2 ** attempt)
    return 0, "(judge failed)"


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
