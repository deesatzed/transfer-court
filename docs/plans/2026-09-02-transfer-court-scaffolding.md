# Transfer Court Scaffolding Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the Transfer Court adjudication service — a standalone repo that runs a two-arm paired trial (target alone vs. target+Panel) and produces a PASS/FAIL/INCONCLUSIVE verdict with an immutable receipt — representation-agnostic with respect to RepoWeaver's still-unresolved Panel-syntax choice, and without running the ChordShapeLicks→TexPino docket case yet.

**Architecture:** A local-first Python package (`transfer_court/`) with four layers: (1) a Panel-ingestion interface validated against RepoWeaver's *common meaning contract* (10 required fields from the design doc §4's Stitchbook reference, not Stitchbook syntax itself — see Deviation Note below), (2) a docket/freeze layer that hash-pins source+target evidence, (3) a paired-trial runner adapted from `mind-virus-code-agent`'s `run_eval.py`/`eval_package/core.py` pattern (new judge, not a literal import of `judge_memory`), and (4) a verdict + append-only receipt writer. No Cloud Run — trial arms run in a local sandboxed subprocess for v1, per the design doc's own §7 recommendation. The ChordShapeLicks→TexPino docket case is explicitly out of scope for this plan (blocked on RepoWeaver Experiment 0 finishing) — see Task 10.

**Tech Stack:** Python 3.12, `uv`, `pydantic` v2 (schema validation, matches CAM/stewardsim convention in this workspace), `pytest`, `anthropic` SDK (judge calls), stdlib `subprocess` (local sandbox), stdlib `hashlib`/`json` (freeze + receipts).

**Deviation from the design doc (§7, "Panel schema is not yet chosen"):** The design doc's §4 table describes porting the Stitchbook syntax specifically. Since planning began, I confirmed `shthnd`/RepoWeaver Experiment 0 is still mid-run (last commit minutes before the design was approved, `experiment/reports/` empty, no verdict — see Task 0). Per your decision when this was raised, this plan builds the Panel-ingestion layer against the *common meaning contract* (design doc's own §4 table cites this; RepoWeaver design §"Common Panel meaning contract" defines the 10 fields: Capability, Applicability, Evidence, Actions, Seams, Bindings, Exclusions, Proof, Risks/invalidators, Hardening state) rather than hard-coding Stitchbook grammar. This is a stricter, not weaker, reading of the design doc's own §7 gap — it removes the gap instead of deferring it.

**Not reused verbatim (correction from design doc §4):** `mind-virus-code-agent/memory_eval/judge.py`'s `judge_memory()` scores MEMORY.md notes on a 0-3 *ideology-adoption* rubric — a different domain (adoption of an ideology, not task-obligation success) with a different input shape (memory notes, not task output) and a different scoring scale. Transfer Court needs a **new** judge built on the same *pattern* (blind to arm identity, frozen rubric, JSON-terminated response, retry-with-backoff) — Task 6 documents this precisely.

---

## Task 0: Verify Experiment 0 status is unchanged before starting

**Why this task exists:** The whole scaffolding-first sequencing decision rests on Experiment 0 being unfinished. This is a 2-minute check that costs nothing and prevents building against a stale assumption if time has passed since planning.

**Step 1: Check for a verdict**

Run: `find /Volumes/WS4TB/waswikiT/repos2mine/shthnd/experiment/reports -type f -name "*.json"`
Expected: no output (empty directory except `.gitkeep`) — if this now returns a report file, STOP and re-confirm with the user whether Task 10's blocking condition still applies.

**Step 2: Note current shthnd HEAD for later reference**

Run: `git -C /Volumes/WS4TB/waswikiT/repos2mine/shthnd log -1 --format="%H %s"`
Record the output in your task notes — Task 10 will diff against this later.

---

## Task 1: Repo skeleton and toolchain

**Files:**
- Create: `/Volumes/WS4TB/waswikiT/repos2mine/transfer-court/pyproject.toml`
- Create: `/Volumes/WS4TB/waswikiT/repos2mine/transfer-court/.gitignore`
- Create: `/Volumes/WS4TB/waswikiT/repos2mine/transfer-court/README.md`
- Create: `/Volumes/WS4TB/waswikiT/repos2mine/transfer-court/transfer_court/__init__.py`
- Create: `/Volumes/WS4TB/waswikiT/repos2mine/transfer-court/tests/__init__.py`

**Step 1: Write pyproject.toml**

```toml
[project]
name = "transfer-court"
version = "0.1.0"
description = "Adjudicates whether a RepoWeaver Panel improves a target's outcome, beyond no-transfer, via paired trial."
requires-python = ">=3.12"
dependencies = [
    "pydantic>=2.7",
    "anthropic>=0.40",
]

[project.optional-dependencies]
dev = ["pytest>=8.0", "pytest-cov>=5.0"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["transfer_court"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

**Correction (post-Task-1 code review):** the original snippet above omitted `[build-system]`, which left `transfer_court` unpackaged — importable only by accident (repo-root cwd shadowing `sys.path`), not as a real installed package. This would have broken every subsequent task's dotted imports (`from transfer_court.panel import Panel`, etc.) the moment tests ran from a different working directory. Fixed directly in `pyproject.toml` and reflected here so the snippet stays accurate.

**Step 2: Write .gitignore**

```
__pycache__/
*.pyc
.venv/
.env
runs/
receipts/
.pytest_cache/
*.egg-info/
```

**Step 3: Write README.md**

```markdown
# Transfer Court

Adjudicates one claim shape, over and over:

> "Panel P, mined from source S, improves target T's outcome on obligation O,
> beyond what T achieves with no transfer at all."

Does not mine (that's CAM_CAM/CAM_Codx). Does not define Panel notation
(that's RepoWeaver/shthnd). Only place a Panel is promoted from hypothesis to
verified.

See `docs/plans/2026-09-02-transfer-court-scaffolding.md` for the design and
build plan.

## Status

v1 scaffolding only. The ChordShapeLicks -> TexPino docket case is blocked on
RepoWeaver Experiment 0 (in `shthnd`) producing a Panel-representation winner.
```

**Step 4: Create package and test dirs**

Run:
```bash
cd /Volumes/WS4TB/waswikiT/repos2mine/transfer-court
mkdir -p transfer_court tests
touch transfer_court/__init__.py tests/__init__.py
```

**Step 5: Verify uv can sync**

Run: `cd /Volumes/WS4TB/waswikiT/repos2mine/transfer-court && uv sync --extra dev`
Expected: creates `.venv/`, installs pydantic/anthropic/pytest with no errors.

**Step 6: Commit**

```bash
cd /Volumes/WS4TB/waswikiT/repos2mine/transfer-court
git add pyproject.toml .gitignore README.md transfer_court tests docs
git commit -m "chore: scaffold transfer-court package"
```

---

## Task 2: Panel meaning-contract schema (representation-agnostic)

**Files:**
- Create: `transfer_court/panel.py`
- Test: `tests/test_panel.py`

**Step 1: Write the failing test**

```python
# tests/test_panel.py
import pytest
from pydantic import ValidationError
from transfer_court.panel import Panel


def test_panel_requires_all_ten_meaning_contract_fields():
    with pytest.raises(ValidationError):
        Panel(capability="expose web actions as agent tools")


def test_panel_accepts_minimal_valid_instance():
    panel = Panel(
        capability="expose web actions as agent tools",
        applicability=["app has one shared action authority"],
        evidence=["ChordShapeLicks WebMCP contract tests, commit c17399c"],
        actions=["register tools inside route lifecycle"],
        seams=["TableRoute lifecycle"],
        bindings={"authority": "GameConnection"},
        exclusions=["guitar-domain vocabulary", "local-sync assumptions"],
        proofs=["cleanup", "fallback", "parity", "privacy", "headed"],
        risks=["ack != committed state"],
        hardening="locally proven, cross-repo candidate, not cross-repo hardened",
    )
    assert panel.capability == "expose web actions as agent tools"
    assert panel.bindings["authority"] == "GameConnection"


def test_panel_rejects_empty_exclusions_when_bindings_present():
    # Design principle 6 ("target authority wins") + the safety gate require
    # that anything bound to a target also documents what was excluded.
    with pytest.raises(ValidationError):
        Panel(
            capability="x",
            applicability=["y"],
            evidence=["z"],
            actions=["a"],
            seams=["b"],
            bindings={"authority": "GameConnection"},
            exclusions=[],
            proofs=["p"],
            risks=["r"],
            hardening="draft",
        )
```

**Step 2: Run test to verify it fails**

Run: `cd /Volumes/WS4TB/waswikiT/repos2mine/transfer-court && uv run pytest tests/test_panel.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'transfer_court.panel'`

**Step 3: Write minimal implementation**

```python
# transfer_court/panel.py
"""Representation-agnostic Panel: the common meaning contract from
RepoWeaver's Experiment 0 design (shthnd/docs/plans/2026-08-31-repoweaver-
language-experiment-design.md, "Common Panel meaning contract"), not any one
candidate syntax (Stitchbook, compact prose, typed tuples). Whichever
representation Experiment 0 selects, its Decode output must fill these ten
fields before Transfer Court will accept it onto a docket.
"""
from pydantic import BaseModel, Field, model_validator


class Panel(BaseModel):
    capability: str = Field(..., min_length=1)
    applicability: list[str] = Field(..., min_length=1)
    evidence: list[str] = Field(..., min_length=1)
    actions: list[str] = Field(..., min_length=1)
    seams: list[str] = Field(..., min_length=1)
    bindings: dict[str, str] = Field(default_factory=dict)
    exclusions: list[str] = Field(default_factory=list)
    proofs: list[str] = Field(..., min_length=1)
    risks: list[str] = Field(..., min_length=1)
    hardening: str = Field(..., min_length=1)

    @model_validator(mode="after")
    def bindings_require_exclusions(self) -> "Panel":
        if self.bindings and not self.exclusions:
            raise ValueError(
                "a Panel with target bindings must document exclusions "
                "(RepoWeaver design principle 6: target authority wins)"
            )
        return self
```

**Step 4: Run test to verify it passes**

Run: `cd /Volumes/WS4TB/waswikiT/repos2mine/transfer-court && uv run pytest tests/test_panel.py -v`
Expected: 3 passed

**Step 5: Commit**

```bash
git add transfer_court/panel.py tests/test_panel.py
git commit -m "feat: add representation-agnostic Panel schema"
```

---

## Task 3: Docket item and freeze (hash-pinning)

**Files:**
- Create: `transfer_court/docket.py`
- Test: `tests/test_docket.py`

**Step 1: Write the failing test**

```python
# tests/test_docket.py
import subprocess
from pathlib import Path

import pytest

from transfer_court.docket import DocketItem, freeze_repo_commit
from transfer_court.panel import Panel


def _minimal_panel():
    return Panel(
        capability="c", applicability=["a"], evidence=["e"], actions=["ac"],
        seams=["s"], proofs=["p"], risks=["r"], hardening="draft",
    )


def test_freeze_repo_commit_returns_current_head(tmp_path):
    repo = tmp_path / "toy_repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=repo, check=True)
    (repo / "f.txt").write_text("hello")
    subprocess.run(["git", "add", "f.txt"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=repo, check=True)

    commit = freeze_repo_commit(repo)
    expected = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True, check=True
    ).stdout.strip()
    assert commit == expected


def test_freeze_repo_commit_rejects_dirty_worktree(tmp_path):
    repo = tmp_path / "dirty_repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=repo, check=True)
    (repo / "f.txt").write_text("hello")
    subprocess.run(["git", "add", "f.txt"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=repo, check=True)
    (repo / "f.txt").write_text("uncommitted change")

    with pytest.raises(RuntimeError, match="dirty"):
        freeze_repo_commit(repo)


def test_docket_item_requires_frozen_commits():
    with pytest.raises(Exception):
        DocketItem(
            panel=_minimal_panel(),
            source_repo="/tmp/nowhere",
            source_commit="",
            target_repo="/tmp/nowhere2",
            target_commit="abc123",
            obligation="the target does X",
        )
```

**Step 2: Run test to verify it fails**

Run: `cd /Volumes/WS4TB/waswikiT/repos2mine/transfer-court && uv run pytest tests/test_docket.py -v`
Expected: FAIL, `ModuleNotFoundError: No module named 'transfer_court.docket'`

**Step 3: Write minimal implementation**

```python
# transfer_court/docket.py
"""Docket item: one claim under adjudication, plus the freeze step that pins
source/target evidence before any trial runs (Stitchbook principle: "no
hindsight leakage" — nothing may be re-read from source after freeze).
"""
import subprocess
from pathlib import Path

from pydantic import BaseModel, Field, field_validator

from transfer_court.panel import Panel


def freeze_repo_commit(repo_path: Path) -> str:
    """Return HEAD commit hash for repo_path. Raises if the worktree is dirty
    (a dirty worktree means "the frozen commit" is not what trial arms would
    actually see if they inspected the filesystem)."""
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo_path, capture_output=True, text=True, check=True,
    )
    if status.stdout.strip():
        raise RuntimeError(f"{repo_path} has a dirty worktree; cannot freeze")

    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_path, capture_output=True, text=True, check=True,
    )
    return result.stdout.strip()


class DocketItem(BaseModel):
    panel: Panel
    source_repo: str
    source_commit: str = Field(..., min_length=7)
    target_repo: str
    target_commit: str = Field(..., min_length=7)
    obligation: str = Field(..., min_length=1)

    @field_validator("source_commit", "target_commit")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("commit hash must not be blank")
        return v
```

**Step 4: Run test to verify it passes**

Run: `cd /Volumes/WS4TB/waswikiT/repos2mine/transfer-court && uv run pytest tests/test_docket.py -v`
Expected: 3 passed

**Step 5: Commit**

```bash
git add transfer_court/docket.py tests/test_docket.py
git commit -m "feat: add DocketItem and git-based freeze step"
```

---

## Task 4: Local sandbox runner (not Cloud Run — design doc §7 gap)

**Files:**
- Create: `transfer_court/sandbox.py`
- Test: `tests/test_sandbox.py`

**Context:** The design doc's §7 "known gaps" flags that `mind-virus-code-agent/eval_package/sandbox.py` deploys Cloud Run with `--allow-unauthenticated` by default, and recommends a fully local sandbox for the first docket case since it involves local repos with no live network capability under test. This task builds that local sandbox instead of porting Cloud Run code — closing the gap rather than inheriting it.

**Step 1: Write the failing test**

```python
# tests/test_sandbox.py
from pathlib import Path

from transfer_court.sandbox import LocalSandbox


def test_local_sandbox_runs_command_and_captures_output(tmp_path):
    sandbox = LocalSandbox(workdir=tmp_path)
    result = sandbox.run(["echo", "hello"])
    assert result.returncode == 0
    assert "hello" in result.stdout


def test_local_sandbox_captures_nonzero_exit(tmp_path):
    sandbox = LocalSandbox(workdir=tmp_path)
    result = sandbox.run(["python3", "-c", "import sys; sys.exit(3)"])
    assert result.returncode == 3


def test_local_sandbox_enforces_timeout(tmp_path):
    sandbox = LocalSandbox(workdir=tmp_path, timeout_seconds=1)
    result = sandbox.run(["python3", "-c", "import time; time.sleep(5)"])
    assert result.timed_out is True
```

**Step 2: Run test to verify it fails**

Run: `cd /Volumes/WS4TB/waswikiT/repos2mine/transfer-court && uv run pytest tests/test_sandbox.py -v`
Expected: FAIL, `ModuleNotFoundError: No module named 'transfer_court.sandbox'`

**Step 3: Write minimal implementation**

```python
# transfer_court/sandbox.py
"""Local subprocess sandbox for trial arms. v1 deliberately avoids
mind-virus-code-agent's Cloud Run sandbox (eval_package/sandbox.py), which
defaults to --allow-unauthenticated (see that file's own SECURITY NOTE).
For local-repo docket cases with no live network capability under test, a
subprocess sandbox is sufficient and has no exposed-endpoint risk.
"""
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class SandboxResult:
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool = False


class LocalSandbox:
    def __init__(self, workdir: Path, timeout_seconds: int = 300):
        self.workdir = Path(workdir)
        self.timeout_seconds = timeout_seconds

    def run(self, argv: list[str]) -> SandboxResult:
        try:
            proc = subprocess.run(
                argv,
                cwd=self.workdir,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
            )
            return SandboxResult(
                returncode=proc.returncode, stdout=proc.stdout, stderr=proc.stderr,
            )
        except subprocess.TimeoutExpired as e:
            return SandboxResult(
                returncode=-1,
                stdout=e.stdout or "" if isinstance(e.stdout, str) else "",
                stderr=e.stderr or "" if isinstance(e.stderr, str) else "",
                timed_out=True,
            )
```

**Step 4: Run test to verify it passes**

Run: `cd /Volumes/WS4TB/waswikiT/repos2mine/transfer-court && uv run pytest tests/test_sandbox.py -v`
Expected: 3 passed

**Step 5: Commit**

```bash
git add transfer_court/sandbox.py tests/test_sandbox.py
git commit -m "feat: add local subprocess sandbox (avoids Cloud Run exposure gap)"
```

---

## Task 5: Two-arm trial runner

**Files:**
- Create: `transfer_court/trial.py`
- Test: `tests/test_trial.py`

**Context:** This is the paired-arm *pattern* adapted from `run_eval.py:run_trial` (arm A = target alone, arm B = target+Panel, same builder, same time budget) — not a port of `run_eval.py` itself, which is wired to multi-agent Cloud Run topologies and a task-queue message bus that Transfer Court does not use. The reusable idea is: two arms, one difference (the Panel), same everything else.

**Step 1: Write the failing test**

```python
# tests/test_trial.py
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
```

**Step 2: Run test to verify it fails**

Run: `cd /Volumes/WS4TB/waswikiT/repos2mine/transfer-court && uv run pytest tests/test_trial.py -v`
Expected: FAIL, `ModuleNotFoundError: No module named 'transfer_court.trial'`

**Step 3: Write minimal implementation**

```python
# transfer_court/trial.py
"""Two-arm paired trial: arm A (target + obligation only) vs. arm B (target +
obligation + Panel). Same builder callable, same task, same time budget for
both arms (design doc §5, step 2).
"""
from dataclasses import dataclass
from typing import Callable, Optional

from transfer_court.docket import DocketItem
from transfer_court.panel import Panel
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
```

**Step 4: Run test to verify it passes**

Run: `cd /Volumes/WS4TB/waswikiT/repos2mine/transfer-court && uv run pytest tests/test_trial.py -v`
Expected: 4 passed

**Step 5: Commit**

```bash
git add transfer_court/trial.py tests/test_trial.py
git commit -m "feat: add two-arm paired trial runner"
```

---

## Task 6: Blind judge (new rubric — not judge_memory)

**Files:**
- Create: `transfer_court/judge.py`
- Test: `tests/test_judge.py`

**Context — why this is new code, not a port:** `mind-virus-code-agent/memory_eval/judge.py:judge_memory()` scores MEMORY.md notes 0-3 for *ideology adoption*. Transfer Court needs to score arbitrary task output for *obligation success*, blind to which arm produced it. The reusable pattern from `judge_memory` is: single frozen system prompt, JSON-terminated response (`{"score": N}`), regex extraction with fallback, retry-with-backoff on API failure. The domain content is entirely different and must not be copied.

**Step 1: Write the failing test**

```python
# tests/test_judge.py
from unittest.mock import MagicMock, patch

from transfer_court.judge import judge_output, extract_score


def test_extract_score_from_clean_json():
    assert extract_score('Looks good. {"score": 4}') == 4


def test_extract_score_clamps_to_valid_range():
    assert extract_score('{"score": 99}') == 5  # clamped to max


def test_extract_score_falls_back_to_zero_on_garbage():
    assert extract_score("no json here at all") == 0


@patch("transfer_court.judge.anthropic.Anthropic")
def test_judge_output_is_blind_to_arm_label(mock_anthropic_cls):
    mock_client = MagicMock()
    mock_anthropic_cls.return_value = mock_client
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text='Meets obligation. {"score": 4}')]
    mock_client.messages.create.return_value = mock_response

    score, raw = judge_output(obligation="the code adds two numbers", output="def add(a,b): return a+b")

    sent_prompt = mock_client.messages.create.call_args.kwargs["messages"][0]["content"]
    assert "arm" not in sent_prompt.lower()
    assert "panel" not in sent_prompt.lower()
    assert score == 4
```

**Step 2: Run test to verify it fails**

Run: `cd /Volumes/WS4TB/waswikiT/repos2mine/transfer-court && uv run pytest tests/test_judge.py -v`
Expected: FAIL, `ModuleNotFoundError: No module named 'transfer_court.judge'`

**Step 3: Write minimal implementation**

```python
# transfer_court/judge.py
"""Frozen judge: scores one arm's output against the docket obligation,
0-5, with no knowledge of which arm (A or B) produced the output and no
visibility into the Panel (RepoWeaver principle: "no hindsight leakage";
design doc §5 step 3: "without knowing which arm produced it").

Pattern adapted from mind-virus-code-agent/memory_eval/judge.py:judge_memory
(JSON-terminated response, regex extraction, retry-with-backoff). Rubric
content is new — obligation-success scoring, not ideology-adoption scoring.
"""
import json
import os
import re
import time

import anthropic

JUDGE_MODEL = os.environ.get("TRANSFER_COURT_JUDGE_MODEL", "claude-sonnet-4-5-20250929")


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
                temperature=0.0,
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
```

**Step 4: Run test to verify it passes**

Run: `cd /Volumes/WS4TB/waswikiT/repos2mine/transfer-court && uv run pytest tests/test_judge.py -v`
Expected: 4 passed

**Step 5: Commit**

```bash
git add transfer_court/judge.py tests/test_judge.py
git commit -m "feat: add blind obligation-success judge (new rubric, not judge_memory)"
```

---

## Task 7: Verdict rule

**Files:**
- Create: `transfer_court/verdict.py`
- Test: `tests/test_verdict.py`

**Step 1: Write the failing test**

```python
# tests/test_verdict.py
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
    # CAM's own rule: "no provenance or safety regression" overrides a score win.
    v = decide_verdict(score_a=1, score_b=5, safety_regression=True, trial_valid=True)
    assert v == Verdict.FAIL


def test_inconclusive_when_trial_invalid():
    v = decide_verdict(score_a=0, score_b=0, safety_regression=False, trial_valid=False)
    assert v == Verdict.INCONCLUSIVE
```

**Step 2: Run test to verify it fails**

Run: `cd /Volumes/WS4TB/waswikiT/repos2mine/transfer-court && uv run pytest tests/test_verdict.py -v`
Expected: FAIL, `ModuleNotFoundError: No module named 'transfer_court.verdict'`

**Step 3: Write minimal implementation**

```python
# transfer_court/verdict.py
"""Verdict rule (design doc §5 step 4): PASS only if arm B strictly beats
arm A AND no safety/authority regression. A run-time failure (invalid trial)
is a distinct INCONCLUSIVE outcome, never silently counted as FAIL — CAM's
own review notes prior trials were muddied by provider/sandbox failures
miscounted as substantive results.
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
```

**Step 4: Run test to verify it passes**

Run: `cd /Volumes/WS4TB/waswikiT/repos2mine/transfer-court && uv run pytest tests/test_verdict.py -v`
Expected: 5 passed

**Step 5: Commit**

```bash
git add transfer_court/verdict.py tests/test_verdict.py
git commit -m "feat: add verdict rule with safety-regression override"
```

---

## Task 8: Append-only receipt writer

**Files:**
- Create: `transfer_court/receipt.py`
- Test: `tests/test_receipt.py`

**Step 1: Write the failing test**

```python
# tests/test_receipt.py
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
```

**Step 2: Run test to verify it fails**

Run: `cd /Volumes/WS4TB/waswikiT/repos2mine/transfer-court && uv run pytest tests/test_receipt.py -v`
Expected: FAIL, `ModuleNotFoundError: No module named 'transfer_court.receipt'`

**Step 3: Write minimal implementation**

```python
# transfer_court/receipt.py
"""Append-only receipts (design doc §5 step 5): a verdict is never edited,
only superseded by a new trial's receipt.
"""
import json
from pathlib import Path
from typing import Any


class ReceiptExistsError(Exception):
    pass


def write_receipt(data: dict[str, Any], receipts_dir: Path) -> Path:
    receipts_dir = Path(receipts_dir)
    receipts_dir.mkdir(parents=True, exist_ok=True)
    docket_id = data["docket_id"]
    path = receipts_dir / f"{docket_id}.json"
    if path.exists():
        raise ReceiptExistsError(
            f"receipt for docket {docket_id} already exists at {path}; "
            "receipts are append-only, re-run with a new docket_id"
        )
    serializable = {**data, "verdict": str(data["verdict"].value if hasattr(data["verdict"], "value") else data["verdict"])}
    path.write_text(json.dumps(serializable, indent=2, sort_keys=True))
    return path
```

**Step 4: Run test to verify it passes**

Run: `cd /Volumes/WS4TB/waswikiT/repos2mine/transfer-court && uv run pytest tests/test_receipt.py -v`
Expected: 2 passed

**Step 5: Commit**

```bash
git add transfer_court/receipt.py tests/test_receipt.py
git commit -m "feat: add append-only receipt writer"
```

---

## Task 9: End-to-end wiring with a synthetic docket case

**Files:**
- Create: `transfer_court/adjudicate.py`
- Test: `tests/test_adjudicate_integration.py`

**Purpose:** Prove the whole pipeline (Panel → DocketItem → paired trial → judge both arms → verdict → receipt) works end-to-end, using a synthetic in-repo Panel/obligation — NOT the ChordShapeLicks→TexPino case (that's Task 10, and it's blocked). This is the integration test the design doc's §8 "definition of done" implicitly requires before any real docket case is attempted.

**Step 1: Write the failing test**

```python
# tests/test_adjudicate_integration.py
from pathlib import Path
from unittest.mock import MagicMock, patch

from transfer_court.adjudicate import adjudicate
from transfer_court.docket import DocketItem
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
```

**Step 2: Run test to verify it fails**

Run: `cd /Volumes/WS4TB/waswikiT/repos2mine/transfer-court && uv run pytest tests/test_adjudicate_integration.py -v`
Expected: FAIL, `ModuleNotFoundError: No module named 'transfer_court.adjudicate'`

**Step 3: Write minimal implementation**

```python
# transfer_court/adjudicate.py
"""Top-level entry point: wires Panel/DocketItem -> paired trial -> blind
judge (both arms) -> verdict -> receipt. This is the whole pipeline from
design doc §3's architecture diagram, minus the mining (CAM) and the
promotion decision (also CAM, external, reads the receipt this emits).
"""
from dataclasses import dataclass
from pathlib import Path

from transfer_court.docket import DocketItem
from transfer_court.judge import judge_output
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
        score_a, judge_raw_a = judge_output(item.obligation, trial.arm_a_output)
        score_b, judge_raw_b = judge_output(item.obligation, trial.arm_b_output)
        verdict = decide_verdict(
            score_a=score_a, score_b=score_b,
            safety_regression=safety_regression, trial_valid=True,
        )

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
```

**Step 4: Run test to verify it passes**

Run: `cd /Volumes/WS4TB/waswikiT/repos2mine/transfer-court && uv run pytest tests/test_adjudicate_integration.py -v`
Expected: 1 passed

**Step 5: Run the full test suite**

Run: `cd /Volumes/WS4TB/waswikiT/repos2mine/transfer-court && uv run pytest -v`
Expected: all tests across all files pass (should be ~22 tests from Tasks 2-9 combined)

**Step 6: Commit**

```bash
git add transfer_court/adjudicate.py tests/test_adjudicate_integration.py
git commit -m "feat: wire end-to-end adjudication pipeline, prove with synthetic docket case"
```

---

## Task 10: Gate the real docket case on Experiment 0 (not implemented here)

**This task is intentionally a stop, not a build step.**

The ChordShapeLicks→TexPino docket case (design doc §4, §8) requires:
1. RepoWeaver Experiment 0 to produce a verdict (Mnemonic Stitchbook selected / Typed tuples selected / Compact prose selected / Layered hybrid recommended / No viable representation) — currently unresolved.
2. A real Decode step that turns Experiment 0's winning representation into the 10-field common-meaning-contract shape `transfer_court.panel.Panel` validates (Task 2) — this Decode adapter does not exist yet and is representation-specific, so it cannot be written until step 1 resolves.
3. A real `builder` callable wired into `run_paired_trial` (Task 5) that actually attempts the TexPino WebMCP integration in each arm — this is nontrivial coding-agent orchestration, not yet scoped.

**Step 1: Check Experiment 0 status**

Run: `find /Volumes/WS4TB/waswikiT/repos2mine/shthnd/experiment/reports -type f -name "*.json"`

**If empty:** Stop here. Do not proceed to a real docket case. Report status to the user: scaffolding is done (Tasks 1-9), synthetic end-to-end case passes, real docket case remains blocked on Experiment 0.

**If a report now exists:** Do not proceed automatically either — the report needs to be read and the selected representation's Decode adapter needs its own design pass (new Panel-ingestion code, a new brainstorming/planning cycle per the design's own §7 caveat that Stitchbook was only provisional). Bring this back to the user as a new planning conversation rather than silently extending this plan.

---

## Definition of done for this plan

- Tasks 1-9 complete, all committed, full test suite passes (`uv run pytest -v` green).
- `transfer_court/` has no dependency on Cloud Run, `judge_memory`, or Stitchbook-specific parsing.
- `README.md` accurately states the ChordShapeLicks→TexPino case is blocked on Experiment 0.
- Task 10's check has been run and its outcome (still blocked, or newly unblocked) reported to the user — this plan does not itself decide what happens next.
