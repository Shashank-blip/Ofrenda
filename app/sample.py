"""Build the sample grave: a tiny library whose last commit is in 2023."""

from __future__ import annotations

import os
import shutil
import stat
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "fixtures" / "hourglass"
AUTHOR = "Nia Calder"
EMAIL = "nia@example.com"

# Each snapshot is the whole tree at that commit. Dates are author dates.
HISTORY = [
    {
        "when": "2021-11-02T09:00:00",
        "message": "Start a duration parser for the kitchen timer",
        "files": {
            "README.md": "# hourglass\n\nParse short durations for a kitchen timer. Minutes work. Hours are next.\n",
            "hourglass.py": '''"""A small parser for kitchen-timer durations."""


def parse_minutes(text: str) -> int:
    """Return a whole number of minutes from a string like '25m'."""
    text = text.strip().lower()
    if text.endswith("m"):
        return int(text[:-1])
    raise ValueError(f"not a minute duration: {text}")
''',
        },
    },
    {
        "when": "2022-01-18T19:40:00",
        "message": "Accept hours as well as minutes",
        "files": {
            "README.md": "# hourglass\n\nParse short durations for a kitchen timer. Minutes and hours work.\n",
            "hourglass.py": '''"""A small parser for kitchen-timer durations."""


def parse_minutes(text: str) -> int:
    """Return a whole number of minutes. '2h' is 120. '25m' is 25."""
    text = text.strip().lower()
    if text.endswith("h"):
        return int(text[:-1]) * 60
    if text.endswith("m"):
        return int(text[:-1])
    raise ValueError(f"not a duration I know: {text}")
''',
        },
    },
    {
        "when": "2022-06-11T11:15:00",
        "message": "Add a test that records days as unfinished",
        "files": {
            "README.md": "# hourglass\n\nParse short durations for a kitchen timer. Minutes and hours work. Days do not.\n",
            "hourglass.py": '''"""A small parser for kitchen-timer durations."""


def parse_minutes(text: str) -> int:
    """Return a whole number of minutes. '2h' is 120. '25m' is 25."""
    text = text.strip().lower()
    if text.endswith("h"):
        return int(text[:-1]) * 60
    if text.endswith("m"):
        return int(text[:-1])
    raise ValueError(f"not a duration I know: {text}")
''',
            "test_hourglass.py": '''from hourglass import parse_minutes


def test_days_are_still_unfinished():
    # TODO: a day should be 24 * 60 minutes. This test is still red.
    try:
        assert parse_minutes("2d") == 2 * 24 * 60
    except ValueError as exc:
        raise AssertionError("days are still unparsed") from exc
''',
        },
    },
    {
        "when": "2022-11-03T21:05:00",
        "message": "Write down that weeks are out of reach for now",
        "files": {
            "README.md": (
                "# hourglass\n\n"
                "Parse short durations for a kitchen timer. Minutes and hours work.\n\n"
                "Weeks are not parsed. The note from November still stands.\n"
            ),
            "hourglass.py": '''"""A small parser for kitchen-timer durations."""


def parse_minutes(text: str) -> int:
    """Return a whole number of minutes. '2h' is 120. '25m' is 25."""
    text = text.strip().lower()
    if text.endswith("h"):
        return int(text[:-1]) * 60
    if text.endswith("m"):
        return int(text[:-1])
    raise ValueError(f"not a duration I know: {text}")
''',
            "test_hourglass.py": '''from hourglass import parse_minutes


def test_days_are_still_unfinished():
    # TODO: a day should be 24 * 60 minutes. This test is still red.
    try:
        assert parse_minutes("2d") == 2 * 24 * 60
    except ValueError as exc:
        raise AssertionError("days are still unparsed") from exc
''',
        },
    },
    {
        "when": "2023-02-14T18:12:00",
        "message": "Leave a warning about months before stopping",
        "files": {
            "README.md": (
                "# hourglass\n\n"
                "Parse short durations for a kitchen timer. Minutes and hours work.\n\n"
                "Weeks are not parsed. The note from November still stands.\n"
            ),
            "hourglass.py": '''"""A small parser for kitchen-timer durations."""


def parse_minutes(text: str) -> int:
    """Return a whole number of minutes. '2h' is 120. '25m' is 25."""
    text = text.strip().lower()
    if text.endswith("h"):
        return int(text[:-1]) * 60
    if text.endswith("m"):
        return int(text[:-1])
    # TODO: months are not the same length. Do not pretend 30 days is honest.
    raise ValueError(f"not a duration I know: {text}")
''',
            "test_hourglass.py": '''from hourglass import parse_minutes


def test_days_are_still_unfinished():
    # TODO: a day should be 24 * 60 minutes. This test is still red.
    try:
        assert parse_minutes("2d") == 2 * 24 * 60
    except ValueError as exc:
        raise AssertionError("days are still unparsed") from exc
''',
        },
    },
]


def _run(repo: Path, args: list[str], env: dict) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=False,
        env=env,
        capture_output=True,
        text=True,
    )


def _commit(repo: Path, message: str, when: str) -> None:
    """Record a commit with git plumbing so a local commit hook cannot rewrite the grave."""
    env = dict(os.environ)
    env.update(
        {
            "GIT_AUTHOR_NAME": AUTHOR,
            "GIT_AUTHOR_EMAIL": EMAIL,
            "GIT_COMMITTER_NAME": AUTHOR,
            "GIT_COMMITTER_EMAIL": EMAIL,
            "GIT_AUTHOR_DATE": when,
            "GIT_COMMITTER_DATE": when,
        }
    )
    added = _run(repo, ["add", "-A"], env)
    if added.returncode != 0:
        raise RuntimeError(added.stderr.strip() or "git add failed")
    tree = _run(repo, ["write-tree"], env)
    if tree.returncode != 0:
        raise RuntimeError(tree.stderr.strip() or "git write-tree failed")
    parent = _run(repo, ["rev-parse", "--verify", "HEAD"], env)
    command = ["commit-tree", tree.stdout.strip(), "-m", message]
    if parent.returncode == 0:
        command.extend(["-p", parent.stdout.strip()])
    created = _run(repo, command, env)
    if created.returncode != 0:
        raise RuntimeError(created.stderr.strip() or "git commit-tree failed")
    ref = "refs/heads/main"
    updated = _run(repo, ["update-ref", ref, created.stdout.strip()], env)
    if updated.returncode != 0:
        raise RuntimeError(updated.stderr.strip() or "git update-ref failed")
    pointed = _run(repo, ["symbolic-ref", "HEAD", ref], env)
    if pointed.returncode != 0:
        raise RuntimeError(pointed.stderr.strip() or "git symbolic-ref failed")


def ensure_sample() -> Path:
    if (SAMPLE / ".git").exists():
        probe = subprocess.run(
            ["git", "-C", str(SAMPLE), "rev-parse", "--verify", "HEAD"],
            capture_output=True,
            text=True,
        )
        if probe.returncode == 0:
            return SAMPLE
    if SAMPLE.exists():
        def _writable(_func, path, _exc):
            os.chmod(path, stat.S_IWRITE)
            os.remove(path)

        shutil.rmtree(SAMPLE, onexc=_writable)
    SAMPLE.mkdir(parents=True)
    subprocess.run(["git", "-C", str(SAMPLE), "init", "-b", "main"], check=True, capture_output=True)
    for commit in HISTORY:
        for relative, content in commit["files"].items():
            destination = SAMPLE / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(content, encoding="utf-8", newline="\n")
        # Drop files that this snapshot no longer has.
        live = set(commit["files"])
        for path in SAMPLE.rglob("*"):
            if ".git" in path.parts or not path.is_file():
                continue
            relative = str(path.relative_to(SAMPLE)).replace("\\", "/")
            if relative not in live:
                path.unlink()
        _commit(SAMPLE, commit["message"], commit["when"])
    return SAMPLE
