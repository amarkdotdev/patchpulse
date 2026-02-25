# AGENTS.md

## Cursor Cloud specific instructions

### Project overview

PatchPulse is a self-hosted Kubernetes risk analysis platform. See `README.md` for full details. The core service is the **FastAPI backend** (`app/backend/`). The Go agent and integrations are optional.

### Running the backend locally

The backend uses SQLite by default for local development (no PostgreSQL required):

```bash
cd app/backend
DATABASE_URL="sqlite:///./patchpulse.db" POLICY_MODE="advisory" uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

- API docs: http://localhost:8000/docs
- Health: http://localhost:8000/health
- AI features work without API keys (rule-based guardrails still function).

### Lint, test, and build

Standard commands are in the `Makefile` (run from `/workspace`), but note the Makefile paths reference `backend/` instead of `app/backend/`. For direct execution:

- **Lint**: `cd app/backend && python3 -m flake8 . --max-line-length=120 --ignore=E501,W503`
- **Test**: `cd app/backend && python3 -m pytest tests/ -v --ignore=tests/test_diff_parser.py`
  - `test_diff_parser.py` has a cross-module import issue (`from integrations.git.github_client`) and must be excluded.
- **Go agent**: `cd app/agent && go vet ./...` (pre-existing unused import warning in `cmd/agent/main.go`)

### Known gotchas

- The `/dashboard` static file mount does not work in local dev mode because the UI path resolution expects Docker paths (`/app/ui`). The dashboard only serves via Docker Compose.
- The `requirements.txt` line `httpx>=0.24.0==0.25.2` is malformed but pip resolves it (installs httpx 0.28.x). This is a pre-existing issue.
- `$HOME/.local/bin` must be on `PATH` for `pytest`, `flake8`, `uvicorn` to be found (pip installs to user site).
- Docker Compose maps backend to **port 8001** (not 8000 as README states).
