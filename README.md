# CodeLens AI

A Python-first hybrid code quality and bug explanation assistant. This is a functional MVP foundation with a React dashboard, FastAPI API, Python AST checks, and optional Ruff/Mypy/Bandit + OpenAI-compatible LLM integration.

## Current MVP scope

- Paste Python code into the analysis workspace.
- Run built-in Python AST checks for syntax errors, `eval`/`exec`, bare `except`, and mutable default arguments.
- Run Ruff, Mypy, and Bandit when installed in the backend environment.
- Merge findings and preserve detection-source provenance.
- View severity, evidence snippets, recommendations, and a transparent heuristic score.
- Ask follow-up questions about a report using an optional OpenAI-compatible LLM endpoint.
- View analysis history for the current backend process.
- Dark developer-focused React UI.

**Important:** The current version deeply analyzes pasted Python snippets only. ZIP ingestion, Git repository cloning, C++ analysis, persistent database history, authentication, and automated code execution are not implemented. Submitted code is never executed.

## Requirements

- Python 3.11+
- Node.js 20+
- npm

## Run locally on Windows PowerShell

### 1. Backend terminal

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python -m uvicorn app.main:app --reload --port 8000
```

Backend health: http://localhost:8000/api/health  
Interactive API docs: http://localhost:8000/docs

If PowerShell blocks activation, use `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` in that terminal, then activate again.

### 2. Frontend terminal

```powershell
cd frontend
npm install
npm run dev
```

Frontend: http://localhost:5173

## Enable AI reasoning and chat

Edit `backend/.env`:

```env
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=your_api_key
LLM_MODEL=gpt-4o-mini
```

For an OpenAI-compatible local Ollama endpoint, use `LLM_BASE_URL=http://localhost:11434/v1` and the model name installed in Ollama. Depending on your Ollama setup, an arbitrary non-empty API key may be required by the compatibility layer. If Ollama runs on the host while the backend runs in Docker, use `http://host.docker.internal:11434/v1` instead of localhost.

Restart FastAPI after editing `.env`. Without an AI provider, static analysis still works; AI chat returns a clear configuration message.

## Docker

Create `backend/.env` from `.env.example`, then run from the project root:

```powershell
docker compose up --build
```

Open http://localhost:5173. Backend API: http://localhost:8000/docs.

## API

- `GET /api/health`
- `POST /api/analyze` with `{ "code": "...", "language": "python", "filename": "example.py", "include_ai": true }`
- `GET /api/history`
- `POST /api/chat` with question, report, and optional finding ID
- `GET /api/settings/provider`

## Scoring note

The displayed score is a simple, documented heuristic that subtracts fixed penalties by finding severity. It is not a measure of program correctness and should not be described as an experimentally validated quality metric. The next research phase should define a labelled benchmark and compare static-only, LLM-only, and hybrid approaches using precision, recall, F1, false-positive rate, and explanation quality.

## Security notes

- The backend writes submitted source to a temporary directory for static analyzers and cleans it up afterward.
- It never executes the submitted source code.
- Analyzer subprocesses use argument arrays (not shell strings) and have timeouts.
- Uploaded archives and Git repositories are not accepted by this MVP, avoiding unsafe ingestion until proper limits and isolation are implemented.
- Do not commit `.env` or expose API keys in frontend code.

## Project structure

```text
codelens-ai/
├── backend/
│   ├── app/
│   │   ├── analyzers/
│   │   │   ├── python_ast.py
│   │   │   └── tool_runner.py
│   │   ├── ai.py
│   │   ├── main.py
│   │   └── schemas.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── lib/api.ts
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   └── styles.css
│   └── Dockerfile
├── docker-compose.yml
└── README.md
```
