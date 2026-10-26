# Ofrenda

A local altar for git repositories that went quiet.

Point it at a folder. Each repository becomes a niche. Ask one to speak, and Gemma, running on this machine through Ollama, answers in the repository's voice. It may only cite commits it was given. Nothing is uploaded.

This is a visit, in the spirit of Día de los Muertos: unfinished work, still on the shelf, spoken for from its own record.

## Run

Install [Ollama](https://ollama.com), then pull Gemma:

```text
ollama pull gemma3:4b
```

From this directory:

```text
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m app
```

Open http://127.0.0.1:8765

Choose **Sit with the sample** to visit `hourglass`, a small duration parser whose last commit is 14 February 2023. Or paste a folder that is a git repository, or a folder that contains some (one level down, up to 24).

If `gemma3:4b` is slow on CPU, set another local tag before starting:

```text
set OFRENDA_MODEL=gemma3:1b
python -m app
```

## What the model is allowed to see

Commit subjects, dates, author names as git recorded them, a short README excerpt, and TODO or FIXME lines. Diffs are not sent. Files named `.env` or ending in `.pem` or `.key` are skipped, so a secret sitting in a note does not enter the prompt. Ollama is called only at `127.0.0.1`.

If the model cites a commit it was not given, that citation is dropped. If nothing it cited was in the packet, the altar refuses the remembrance and leaves the git inscription in place.

## Tests

```text
pytest
```

## License

MIT.
