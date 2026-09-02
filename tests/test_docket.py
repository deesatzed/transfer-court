import subprocess
from pathlib import Path

import pytest

from pydantic import ValidationError

from transfer_court.docket import DocketItem, FreezeError, freeze_repo_commit
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


def test_freeze_repo_commit_raises_freeze_error_on_non_git_directory(tmp_path):
    not_a_repo = tmp_path / "not_a_repo"
    not_a_repo.mkdir()

    with pytest.raises(FreezeError, match="not a valid git repository"):
        freeze_repo_commit(not_a_repo)


def test_docket_item_rejects_whitespace_only_commit_hash():
    # 7+ whitespace chars pass Field(min_length=7) but must still be caught
    # by the not_blank validator.
    with pytest.raises(ValidationError, match="must not be blank"):
        DocketItem(
            panel=_minimal_panel(),
            source_repo="/tmp/nowhere",
            source_commit="       ",
            target_repo="/tmp/nowhere2",
            target_commit="abc1234",
            obligation="the target does X",
        )
