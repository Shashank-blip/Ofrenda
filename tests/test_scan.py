import json
import os
import subprocess
from datetime import date
from pathlib import Path

import pytest

from app.remember import build_packet
from app.scan import ScanError, quiet_label, read_grave, scan_folder


def git_env(when: str | None = None) -> dict:
    env = dict(os.environ)
    env.update(
        {
            "GIT_AUTHOR_NAME": "Nia Calder",
            "GIT_AUTHOR_EMAIL": "nia@example.com",
            "GIT_COMMITTER_NAME": "Nia Calder",
            "GIT_COMMITTER_EMAIL": "nia@example.com",
        }
    )
    if when:
        env["GIT_AUTHOR_DATE"] = when
        env["GIT_COMMITTER_DATE"] = when
    return env


def run_git(repo: Path, args: list[str], when: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=False,
        env=git_env(when),
        capture_output=True,
        text=True,
    )


def commit(repo: Path, message: str, when: str) -> None:
    added = run_git(repo, ["add", "-A"], when)
    assert added.returncode == 0, added.stderr
    tree = run_git(repo, ["write-tree"], when)
    assert tree.returncode == 0, tree.stderr
    parent = run_git(repo, ["rev-parse", "--verify", "HEAD"], when)
    command = ["commit-tree", tree.stdout.strip(), "-m", message]
    if parent.returncode == 0:
        command.extend(["-p", parent.stdout.strip()])
    created = run_git(repo, command, when)
    assert created.returncode == 0, created.stderr
    updated = run_git(repo, ["update-ref", "refs/heads/main", created.stdout.strip()], when)
    assert updated.returncode == 0, updated.stderr
    pointed = run_git(repo, ["symbolic-ref", "HEAD", "refs/heads/main"], when)
    assert pointed.returncode == 0, pointed.stderr


def make_repo(path: Path, when: str, message: str) -> None:
    path.mkdir(parents=True)
    assert run_git(path, ["init", "-b", "main"]).returncode == 0
    (path / "README.md").write_text("# Lamp\n\nA small light.\n", encoding="utf-8")
    (path / "lamp.py").write_text("x = 1\n# TODO: replace the wick\n", encoding="utf-8")
    (path / ".env").write_text("SECRET_TOKEN=hunter2\n# TODO: do not leak hunter2\n", encoding="utf-8")
    commit(path, message, when)


def test_quiet_label_units():
    assert quiet_label(1) == "quiet for 1 day"
    assert quiet_label(12) == "quiet for 12 days"
    assert quiet_label(400) == "quiet for 13 months"
    assert quiet_label(800) == "quiet for 2.2 years"


def test_grave_reads_history_and_skips_secrets(tmp_path: Path):
    repo = tmp_path / "lamp"
    make_repo(repo, "2021-04-02T10:00:00", "First light")
    (repo / "lamp.py").write_text("x = 2\n# TODO: replace the wick\n", encoding="utf-8")
    commit(repo, "Leave the wick for later", "2023-02-14T18:00:00")

    grave = read_grave(repo)
    expected_quiet = (date.today() - date(2023, 2, 14)).days
    assert grave["name"] == "lamp"
    assert grave["lifespan"] == "2021–2023"
    assert grave["quiet_days"] == expected_quiet
    assert grave["last_subject"] == "Leave the wick for later"
    assert grave["commit_count"] == 2
    blob = json.dumps(build_packet(grave))
    assert "hunter2" not in blob
    assert "replace the wick" in blob
    assert "Leave the wick for later" in blob


def test_folder_finds_child_repo_not_plain_directories(tmp_path: Path):
    make_repo(tmp_path / "old" / "lamp", "2020-01-01T00:00:00", "Set it down")
    (tmp_path / "notes").mkdir()
    graves, truncated = scan_folder(tmp_path)
    assert truncated is False
    assert [grave["name"] for grave in graves] == ["lamp"]


def test_missing_folder_is_an_error(tmp_path: Path):
    with pytest.raises(ScanError):
        scan_folder(tmp_path / "nowhere")
