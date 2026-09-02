from pathlib import Path

import pytest

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


def test_local_sandbox_captures_missing_command_without_raising(tmp_path):
    sandbox = LocalSandbox(workdir=tmp_path)
    result = sandbox.run(["this-command-does-not-exist-anywhere"])
    assert result.returncode != 0
    assert "this-command-does-not-exist-anywhere" in result.stderr


def test_local_sandbox_rejects_nonexistent_workdir_at_construction(tmp_path):
    missing = tmp_path / "does-not-exist"
    with pytest.raises(NotADirectoryError):
        LocalSandbox(workdir=missing)
