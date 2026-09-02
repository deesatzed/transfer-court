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
        workdir = Path(workdir)
        if not workdir.is_dir():
            raise NotADirectoryError(f"sandbox workdir does not exist: {workdir}")
        self.workdir = workdir
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
        except FileNotFoundError as e:
            # A trial arm's command referencing a program that does not
            # exist is a normal (if unsuccessful) trial outcome, not an
            # exceptional condition in the sandbox itself — report it the
            # same way a nonzero exit code is reported, rather than raising
            # and crashing the caller (the paired trial runner).
            return SandboxResult(returncode=127, stdout="", stderr=str(e))
