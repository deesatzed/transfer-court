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
