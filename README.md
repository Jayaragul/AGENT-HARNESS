# Factory AI Copilot

An industrial AI assistant for factory operations — check inventory, analyze machine requirements, and generate risk reports through a clean ChatGPT-like interface.

## Quick Start

```bash
cd factory-agent
pip install -r requirements.txt
cp .env.example .env   # Set BACKEND and API keys
uvicorn web_app:app --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000`.

## Architecture

```
User query → AgentHarness → LLM planner → Tool execution → Response
```

- **LLM planner** (Gemini 2.5 Flash) decides which tools to call
- **Deterministic Python tools** handle all calculations (material sufficiency, machine hours, risk scoring)
- **Wiki layer** persists results for compounding knowledge across sessions

## Available Skills

| Skill | What it does |
|---|---|
| Material Sufficiency | Checks if inventory can fulfill an order |
| Machine Requirements | Calculates machine time and cost for an order |
| Material Risk Report | Identifies material shortages across all orders |

## Configuration

| Variable | Default | Description |
|---|---|---|
| `BACKEND` | `CODEX` | `CODEX`, `GEMINI`, or `MOCK` |
| `OPENAI_API_KEY` | — | Required for CODEX |
| `GEMINI_API_KEY` | — | Required for GEMINI |

Start with `BACKEND=MOCK` to test without an API key.

## Project Structure

```
factory-agent/
├── web_app.py              # FastAPI server
├── static/index.html       # Chat UI
├── agent/                  # Orchestration layer
├── models/                 # LLM backends (CODEX, GEMINI, MOCK)
├── tools/                  # Deterministic calculation tools
├── skills/                 # Skill handlers
├── data_access/            # CSV loading and querying
├── guardrails/             # Input and output validation
├── output_service/         # Report generation
├── data/                   # Sample factory CSV data
└── wiki/                   # Persistent knowledge base
```

## API

```bash
POST /api/chat    { "query": "Do we have enough fabric for ORD-1001?" }
GET  /api/dashboard   # KPIs: active orders, machine status, inventory health
GET  /api/tools       # List available tools
```
