# PatchPulse Backend

FastAPI control plane with policy engine for risk analysis and guardrail enforcement.

## How to Run

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL="sqlite:///./patchpulse.db"
export POLICY_MODE="advisory"

# Run server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### With Docker

```bash
docker build -t patchpulse-backend .
docker run -p 8000:8000 -e DATABASE_URL="sqlite:///./patchpulse.db" patchpulse-backend
```

## Environment Variables

- `DATABASE_URL`: Database connection string (default: `sqlite:///./patchpulse.db`)
- `POLICY_MODE`: Policy enforcement mode: `advisory` or `enforce` (default: `advisory`)
- `LOG_LEVEL`: Logging level (default: `INFO`)

## API Endpoints

- `GET /health`: Health check
- `GET /metrics`: Prometheus metrics
- `POST /api/v1/change-events`: Create change event and evaluate policy
- `POST /api/v1/cluster-signals`: Create cluster signals
- `GET /api/v1/decisions`: List recent decisions
- `GET /api/v1/decisions/{id}`: Get decision details
- `GET /api/v1/change-events/{id}`: Get change event details

## Policy Engine

The policy engine evaluates guardrails and calculates risk scores. See `policy_engine.py` for guardrail implementations.

## Testing

```bash
pytest tests/
```

