"""Read git facts for a repository. No network, no diffs, no secrets."""

from __future__ import annotations

import os
import subprocess
from datetime import date
from pathlib import Path

SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    "build",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
}
SOURCE_SUFFIXES = {
    ".py",
    ".md",
    ".txt",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".go",
    ".rs",
    ".java",
    ".rb",
    ".c",
    ".h",
    ".cpp",
    ".cs",
    ".toml",
    ".yml",
    ".yaml",
    ".html",
    ".css",
}
SECRET_SUFFIXES = (".pem", ".key", ".p12", ".pfx")
MAX_REPOS = 24
MAX_TODOS = 20
MAX_COMMITS = 12
README_CAP = 1500


class ScanError(Exception):
    pass


def quiet_label(days: int) -> str:
    if days < 45:
        unit = "day" if days == 1 else "days"
        return f"quiet for {days} {unit}"
    if days < 730:
        months = max(1, round(days / 30.44))
        unit = "month" if months == 1 else "months"
        return f"quiet for {months} {unit}"
    years = days / 365.25
    if years < 10:
        text = f"{years:.1f}".rstrip("0").rstrip(".")
        unit = "year" if text == "1" else "years"
        return f"quiet for {text} {unit}"
    return f"quiet for {int(years)} years"


def lifespan(first_on: str, last_on: str) -> str:
    start, end = first_on[:4], last_on[:4]
    if start == end:
        return start
    return f"{start}–{end}"


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=15,
    )


def _repo_root(path: Path) -> Path | None:
    try:
        result = _git(path, "rev-parse", "--show-toplevel")
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    text = result.stdout.strip()
    if not text:
        return None
    return Path(text).resolve()


def _iter_children(path: Path):
    try:
        entries = list(path.iterdir())
    except OSError:
        return
    for entry in entries:
        if entry.name in SKIP_DIRS or entry.is_symlink() or not entry.is_dir():
            continue
        yield entry


def _same(left: Path | None, right: Path) -> bool:
    if left is None:
        return False
    return os.path.normcase(str(left)) == os.path.normcase(str(right.resolve()))


def find_repos(root: Path, limit: int = MAX_REPOS) -> tuple[list[Path], bool]:
    root = root.resolve()
    if not root.exists() or not root.is_dir():
        raise ScanError(f"That folder does not exist: {root}")
    if _same(_repo_root(root), root):
        return [root], False

    found: list[Path] = []
    saw_extra = False
    for child in _iter_children(root):
        if _same(_repo_root(child), child):
            if len(found) >= limit:
                saw_extra = True
                break
            found.append(child.resolve())
        else:
            for grand in _iter_children(child):
                if _same(_repo_root(grand), grand):
                    if len(found) >= limit:
                        saw_extra = True
                        break
                    found.append(grand.resolve())
            if saw_extra:
                break
    return found, saw_extra


def _is_secret(path: Path) -> bool:
    name = path.name.lower()
    if name == ".env" or name.startswith(".env"):
        return True
    if name in {"credentials.json", "secrets.json", "id_rsa", "id_dsa"}:
        return True
    return name.endswith(SECRET_SUFFIXES)


def _readme(repo: Path) -> str:
    for entry in repo.iterdir():
        if entry.is_file() and entry.name.lower() in {"readme.md", "readme.txt", "readme"}:
            try:
                return entry.read_text(encoding="utf-8", errors="replace")[:README_CAP]
            except OSError:
                return ""
    return ""


def _todos(repo: Path) -> list[dict]:
    found: list[dict] = []
    for dirpath, dirnames, filenames in os.walk(repo, followlinks=False):
        dirnames[:] = [name for name in dirnames if name not in SKIP_DIRS and not name.startswith(".")]
        for filename in filenames:
            if len(found) >= MAX_TODOS:
                return found
            path = Path(dirpath) / filename
            if _is_secret(path) or path.suffix.lower() not in SOURCE_SUFFIXES:
                continue
            try:
                if path.stat().st_size > 200_000:
                    continue
                lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
            except OSError:
                continue
            for number, line in enumerate(lines, start=1):
                lower = line.lower()
                if "todo" not in lower and "fixme" not in lower:
                    continue
                text = line.strip()
                if len(text) > 240:
                    text = text[:240]
                found.append(
                    {
                        "file": str(path.relative_to(repo)).replace("\\", "/"),
                        "line": number,
                        "text": text,
                    }
                )
                if len(found) >= MAX_TODOS:
                    return found
    return found


def _commits(repo: Path) -> list[dict]:
    result = _git(repo, "log", f"-n{MAX_COMMITS}", "--pretty=format:%h%x09%aI%x09%an%x09%s")
    if result.returncode != 0 or not result.stdout.strip():
        raise ScanError("This repository has no commits yet.")
    commits = []
    for line in result.stdout.splitlines():
        parts = line.split("\t", 3)
        if len(parts) != 4:
            continue
        sha, authored, author, subject = parts
        commits.append(
            {
                "sha": sha,
                "date": authored[:10],
                "author": author,
                "subject": subject,
            }
        )
    if not commits:
        raise ScanError("This repository has no commits yet.")
    return commits


def read_grave(path: Path) -> dict:
    path = path.resolve()
    root = _repo_root(path)
    if root is None:
        raise ScanError(f"Not a git repository: {path}")
    commits = _commits(root)
    count = _git(root, "rev-list", "--count", "HEAD")
    commit_count = int(count.stdout.strip()) if count.returncode == 0 and count.stdout.strip().isdigit() else len(commits)
    roots = _git(root, "rev-list", "--max-parents=0", "HEAD")
    root_sha = roots.stdout.splitlines()[0] if roots.returncode == 0 and roots.stdout.strip() else ""
    first = _git(root, "show", "-s", "--pretty=format:%aI", root_sha) if root_sha else commits[-1]
    first_on = (first.stdout.strip() if root_sha else commits[-1]["date"])[:10]
    last_on = commits[0]["date"]
    quiet_days = max(0, (date.today() - date.fromisoformat(last_on)).days)
    return {
        "path": str(root),
        "name": root.name,
        "first_on": first_on,
        "last_on": last_on,
        "lifespan": lifespan(first_on, last_on),
        "quiet_days": quiet_days,
        "quiet_label": quiet_label(quiet_days),
        "last_subject": commits[0]["subject"],
        "last_author": commits[0]["author"],
        "commit_count": commit_count,
        "readme_excerpt": _readme(root),
        "todos": _todos(root),
        "commits": commits,
    }


def scan_folder(path: str | Path) -> tuple[list[dict], bool]:
    repos, truncated = find_repos(Path(path))
    graves = []
    for repo in repos:
        try:
            graves.append(read_grave(repo))
        except ScanError:
            continue
    graves.sort(key=lambda grave: grave["quiet_days"], reverse=True)
    return graves, truncated
