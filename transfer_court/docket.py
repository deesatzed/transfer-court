"""Docket item: one claim under adjudication, plus the freeze step that pins
source/target evidence before any trial runs (Stitchbook principle: "no
hindsight leakage" — nothing may be re-read from source after freeze).
"""
import subprocess
from pathlib import Path

from pydantic import BaseModel, Field, field_validator

from transfer_court.panel import Panel


class FreezeError(RuntimeError):
    """Raised when a repo cannot be frozen to a commit (dirty worktree, not a
    git repo, or path does not exist)."""


def _run_git(repo_path: Path, args: list[str]) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=repo_path, capture_output=True, text=True, check=True,
        )
    except subprocess.CalledProcessError as e:
        raise FreezeError(
            f"{repo_path} is not a valid git repository: {e.stderr.strip()}"
        ) from e
    except FileNotFoundError as e:
        raise FreezeError(f"{repo_path} does not exist: {e}") from e
    return result.stdout


def freeze_repo_commit(repo_path: Path) -> str:
    """Return HEAD commit hash for repo_path. Raises if the worktree is dirty
    (a dirty worktree means "the frozen commit" is not what trial arms would
    actually see if they inspected the filesystem)."""
    status = _run_git(repo_path, ["status", "--porcelain"])
    if status.strip():
        raise FreezeError(f"{repo_path} has a dirty worktree; cannot freeze")

    return _run_git(repo_path, ["rev-parse", "HEAD"]).strip()


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
