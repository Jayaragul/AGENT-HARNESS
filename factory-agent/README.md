# Factory Agent

This directory contains the runnable agent, API, tests, and behavioral evaluation harness. See the [repository README](../README.md) for architecture, setup, quality results, and interview guidance.

```bash
pip install -r requirements.txt
pytest --cov --cov-report=term-missing
python -m evals.runner
BACKEND=MOCK uvicorn web_app:app --host 0.0.0.0 --port 8000
```

To use the local Codex account instead of an API key, install and sign in to
Codex CLI, then set `BACKEND=CODEX_CLI` in `.env`. Each request runs ephemerally
in a temporary directory with read-only sandboxing.
