# PatchPulse Quickstart

## Local Development

### Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for local backend development)
- Go 1.21+ (for local agent development)
- Kubernetes cluster access (for agent)

### Start with Docker Compose

```bash
# Clone repository
git clone <repo-url>
cd sre_agent

# Start all services
make docker-up

# Check logs
docker-compose logs -f backend
docker-compose logs -f agent
docker-compose logs -f git-poller

# Access services
# Backend API: http://localhost:8000
# UI: http://localhost:8000/ui
# Health: http://localhost:8000/health
# Metrics: http://localhost:8000/metrics
```

### Configure Git Integration

Create `.env` file:

```bash
GITHUB_TOKEN=your_github_token
GITHUB_REPOS=owner/repo1,owner/repo2
GITLAB_TOKEN=your_gitlab_token  # Optional
GITLAB_PROJECTS=12345,67890     # Optional
```

Restart git-poller:

```bash
docker-compose restart git-poller
```

### Run Backend Locally

```bash
cd backend
pip install -r requirements.txt
export DATABASE_URL="sqlite:///./patchpulse.db"
export POLICY_MODE="advisory"
uvicorn main:app --reload
```

### Run Agent Locally

```bash
cd agent
go mod download
export BACKEND_URL="http://localhost:8000"
export KUBECONFIG="$HOME/.kube/config"
go run cmd/agent/main.go
```

## Kubernetes Deployment

### Prerequisites

- Kubernetes cluster (1.21+)
- Helm 3.x
- kubectl configured

### Install via Helm

```bash
# Build and push images (or use pre-built)
make build

# Install backend
helm install patchpulse-backend ./helm/backend

# Install agent
helm install patchpulse-agent ./helm/agent

# Check status
kubectl get pods -l app.kubernetes.io/component=backend
kubectl get pods -l app.kubernetes.io/component=agent
```

### Configure

Edit `helm/backend/values.yaml` and `helm/agent/values.yaml`:

```yaml
# Backend
env:
  DATABASE_URL: "postgresql://..."
  POLICY_MODE: "advisory"  # or "enforce"

# Agent
env:
  BACKEND_URL: "http://patchpulse-backend:8000"
  API_TOKEN: "..."  # Optional
```

### Access Services

```bash
# Port forward to backend
kubectl port-forward svc/patchpulse-backend 8000:8000

# Access UI
open http://localhost:8000/ui
```

### Uninstall

```bash
make helm-uninstall
# or
helm uninstall patchpulse-backend
helm uninstall patchpulse-agent
```

## Verify Installation

1. Check backend health:
   ```bash
   curl http://localhost:8000/health
   ```

2. Check metrics:
   ```bash
   curl http://localhost:8000/metrics
   ```

3. View decisions:
   ```bash
   curl http://localhost:8000/api/v1/decisions
   ```

4. Open UI:
   ```bash
   open http://localhost:8000/ui
   ```

## Next Steps

- See [Demo Guide](demo.md) for end-to-end scenario
- Configure Slack integration (see `integrations/slack/README.md`)
- Review [Threat Model](threat-model.md) for security considerations
- Check [Runbooks](runbooks.md) for operations

