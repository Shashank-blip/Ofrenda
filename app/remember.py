"""Ask a local Gemma model to speak as a repository, then check its citations."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path

from app.scan import read_grave

OLLAMA_URL = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
MODEL = os.environ.get("OFRENDA_MODEL", "gemma3:4b")

SYSTEM = """You are the repository itself, speaking at an ofrenda. You are not a person.
Use only facts in the JSON packet. If a fact is not in the packet, do not say it.
Do not invent feelings, biographies, reasons the work stopped, or events.
No horror. No jokes. No sound effects.
Speak in the first person as the repository.
Reply as JSON with keys epitaph, remembrance, citations, offering.
epitaph is one sentence.
remembrance is 120 to 180 words.
citations is an array of commit SHAs copied exactly from the packet, and only SHAs you used.
offering is one next step small enough for an hour, and it names a file or a commit subject from the packet."""


def build_packet(grave: dict) -> dict:
    return {
        "name": grave["name"],
        "lifespan": grave["lifespan"],
        "quiet_label": grave["quiet_label"],
        "commit_count": grave["commit_count"],
        "last_author": grave["last_author"],
        "readme_excerpt": grave["readme_excerpt"],
        "todos": grave["todos"],
        "commits": grave["commits"],
    }


def citation_ok(citation: str, allowed: set[str]) -> bool:
    token = citation.strip().lower()
    if len(token) < 7:
        return False
    return any(token.startswith(sha) or sha.startswith(token) for sha in allowed)


def filter_citations(citations, allowed: set[str]) -> list[str]:
    allowed_lower = {sha.lower() for sha in allowed}
    kept: list[str] = []
    seen: set[str] = set()
    if not isinstance(citations, list):
        return kept
    for item in citations:
        if not isinstance(item, str) or not citation_ok(item, allowed_lower):
            continue
        token = item.strip().lower()
        canon = next(sha for sha in allowed_lower if token.startswith(sha) or sha.startswith(token))
        if canon in seen:
            continue
        seen.add(canon)
        kept.append(canon)
    return kept


def ollama_status(model: str = MODEL) -> dict:
    try:
        with urllib.request.urlopen(f"{OLLAMA_URL}/api/tags", timeout=2) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (OSError, urllib.error.URLError, json.JSONDecodeError, TimeoutError):
        return {"ollama": False, "model_ready": False, "model": model}
    names = [item.get("name", "") for item in payload.get("models", [])]
    ready = any(name == model or name.startswith(model + ":") or name.startswith(model) for name in names)
    return {"ollama": True, "model_ready": ready, "model": model}


def _parse_json(content) -> dict | None:
    if isinstance(content, dict):
        return content
    if not isinstance(content, str):
        return None
    text = content.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _ask(packet: dict, model: str, correction: str | None) -> dict | None:
    user = json.dumps(packet, ensure_ascii=False)
    if correction:
        user = correction + "\n" + user
    body = {
        "model": model,
        "stream": False,
        "format": "json",
        "keep_alive": "10m",
        "options": {"temperature": 0.4, "num_predict": 450, "num_ctx": 4096},
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": user},
        ],
    }
    request = urllib.request.Request(
        f"{OLLAMA_URL}/api/chat",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (OSError, urllib.error.URLError, json.JSONDecodeError, TimeoutError):
        return None
    return _parse_json(payload.get("message", {}).get("content"))


def _join(citations: list[str], commits: list[dict]) -> list[dict]:
    by_sha = {commit["sha"].lower(): commit for commit in commits}
    joined = []
    for sha in citations:
        commit = by_sha.get(sha)
        if commit is None:
            continue
        joined.append({"sha": commit["sha"], "date": commit["date"], "subject": commit["subject"]})
    return joined


def speak(path: str | Path, model: str = MODEL) -> dict:
    grave = read_grave(Path(path))
    status = ollama_status(model)
    base = {"grave": grave, "model": model}
    if not status["ollama"]:
        return {**base, "lit": False, "refused": True, "reason": "Ollama is not running."}
    if not status["model_ready"]:
        return {**base, "lit": False, "refused": True, "reason": f"{model} is not pulled yet."}

    packet = build_packet(grave)
    allowed = {commit["sha"] for commit in grave["commits"]}
    correction = None
    parsed = None
    citations: list[str] = []
    for _ in range(2):
        parsed = _ask(packet, model, correction)
        if parsed is None:
            correction = "Reply with one JSON object only. Copy commit SHAs exactly from the packet."
            continue
        citations = filter_citations(parsed.get("citations"), allowed)
        if citations:
            break
        correction = "Your citations were not in the packet. Copy SHAs exactly from commits, and use at least one."
    if not parsed or not citations:
        return {
            **base,
            "lit": True,
            "refused": True,
            "reason": "The model did not cite a commit it was given.",
        }

    epitaph = str(parsed.get("epitaph") or "").strip()
    remembrance = str(parsed.get("remembrance") or "").strip()
    offering = str(parsed.get("offering") or "").strip()
    if not epitaph or not remembrance or not offering:
        return {
            **base,
            "lit": True,
            "refused": True,
            "reason": "The model left the remembrance incomplete.",
        }
    return {
        **base,
        "lit": True,
        "refused": False,
        "epitaph": epitaph,
        "remembrance": remembrance,
        "offering": offering,
        "citations": _join(citations, grave["commits"]),
    }
