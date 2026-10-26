# Ofrenda

Hacktoberfest Open-Source AI Challenge Week 4: Ghost in the Machine

This is a submission for the Hacktoberfest Open-Source AI Challenge Week 4: Ghost in the Machine.

## What I Built

Some folders are cemeteries of unfinished work. The last commit is still the inscription on the stone, and nobody has read it in years.

Ofrenda is a local altar for those repositories. You point it at a folder on your machine. Each git repo that went quiet becomes a niche: the years it was alive, how long it has been dark, and its last commit subject. A longer quiet means a lower flame.

Ask one to speak. Gemma 3, running on this computer through Ollama, answers in the repository's voice. It may only use the record it was handed: commit subjects, dates, the author name as git wrote it, a short README, and TODO lines. The server drops any commit id the model invents. If nothing it cited was real, the altar refuses the remembrance and leaves the inscription in place.

The sample grave is `hourglass`, a tiny duration parser whose last commit is 14 February 2023. On this machine Gemma said:

> The parsing of time ceased within these boundaries.

It cited all five commits, from "Start a duration parser for the kitchen timer" through "Leave a warning about months before stopping," and the offering was a real file: `test_hourglass.py`. It did not invent a person. The ghost is the repository.

## Demo

The app runs locally.

```text
ollama pull gemma3:4b
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m app
```

Open http://127.0.0.1:8765 and choose **Sit with the sample**. Or paste a folder that is a repository, or that contains some.

If the 4B model is slow on CPU:

```text
set OFRENDA_MODEL=gemma3:1b
```

## Code

https://github.com/Shashank-blip/Ofrenda

## How I Built It

Python and FastAPI serve one page. There is no database and no account. Git is read with `git log` and a walk for TODO lines. Diffs are not sent. Files named `.env`, and names that look like keys, are left out of the packet, so a secret in a note does not become part of the prompt.

The model call is Ollama at `127.0.0.1`, `gemma3:4b`, JSON output, and a small context window so a laptop without a discrete GPU can hold it. This machine has Intel Iris Xe graphics. The 4B model still answered.

The check that matters is small and tested without the model: a citation has to match a SHA that was in the packet. Unknown ids are dropped. An empty citation list is a refusal, not a story.

## Why open innovation matters

A closed model would have meant uploading unfinished work: half-written TODOs, private commit subjects, the names of the people who touched the code. The dead, in this sense, should be visited at home.

Gemma is an open-weight model. Ollama runs it on the machine. After the weights are downloaded, the altar does not need the network to speak. The weights can be swapped with `OFRENDA_MODEL`. Nothing about the remembrance is locked inside a hosted service that could disappear and take the voice with it.

## Prize Categories

- Best Use of Gemma
