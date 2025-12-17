# Outbound Email Guard

An “Outbound Email Guard” agent that reviews outbound emails for compliance issues and iteratively rewrites them until they pass. The backend streams agent progress to the web UI via Server-Sent Events (SSE).

## Prerequisites

- `uv` (Python package + environment manager): https://docs.astral.sh/uv/
- Python `>=3.12` (uv can install/manage this for you)
- `OPENROUTER_API_KEY` (get one from [OpenRouter](https://openrouter.ai/))

## Setup (uv)

Create a virtualenv and install dependencies:

```bash
uv python install 3.12
uv venv
uv sync
```

Configure env vars (required for the agent LLM calls):

```bash
cp .env.example .env 2>/dev/null || true
```

Then edit `.env` and set:

- `OPENROUTER_API_KEY="..."`
- Optional: `OPENROUTER_MODEL="openai/gpt-4o-mini"`

## Activate the venv

macOS/Linux:

```bash
source .venv/bin/activate
```

Windows (PowerShell):

```powershell
.venv\\Scripts\\Activate.ps1
```

Alternatively, you can skip activation and prefix commands with `uv run ...`.

## Run the server

Option A (with activated venv):

```bash
python server.py
```

Option B (no activation):

```bash
uv run python server.py
```

Development mode (auto-reload):

```bash
uv run uvicorn server:app --reload --host 0.0.0.0 --port 8000
```

Open the web UI:

- `http://localhost:8000`
