"""
Git repository introspection.

Used to stamp every benchmark report with the commit and branch it was
generated from, so a regression found later (e.g. via
`benchmarks/regression/`) can be traced back to what actually changed
between two runs, rather than just the metric delta.
"""

from __future__ import annotations

import subprocess


def _run_git(*args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", *args],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
    except (
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
        FileNotFoundError,
    ):
        return None

    output = result.stdout.strip()

    return output or None


def get_git_commit() -> str | None:
    """
    Full SHA of the currently checked-out commit, or None if not running
    inside a git repository (or git is unavailable).
    """

    return _run_git("rev-parse", "HEAD")


def get_git_branch() -> str | None:
    """
    Current branch name, or None if not running inside a git repository,
    git is unavailable, or HEAD is detached.
    """

    branch = _run_git("rev-parse", "--abbrev-ref", "HEAD")

    return None if branch == "HEAD" else branch
