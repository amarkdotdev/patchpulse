# PatchPulse UI

Minimal web interface for viewing risk analysis decisions.

## Features

- List recent decisions with risk scores
- View detailed decision information
- See guardrails triggered and evidence
- View change event details

## Access

The UI is served by the FastAPI backend at `/ui` when running.

## Local Development

The UI is static HTML/CSS/JS. To develop locally:

1. Serve the `ui/` directory with any static file server
2. Update `API_BASE` in `index.html` to point to your backend

```bash
# Using Python
cd ui
python -m http.server 8080

# Or using Node.js
npx serve ui
```

## API Integration

The UI calls the following backend endpoints:
- `GET /api/v1/decisions` - List decisions
- `GET /api/v1/decisions/{id}` - Get decision details
- `GET /api/v1/change-events/{id}` - Get change event details

