# PatchPulse Agent

Go-based Kubernetes agent that collects cluster events and resource snapshots.

## How to Run

### Local Development

```bash
# Build
go build -o agent ./cmd/agent

# Set environment variables
export BACKEND_URL="http://localhost:8000"
export KUBECONFIG="$HOME/.kube/config"

# Run
./agent
```

### With Docker

```bash
docker build -t patchpulse-agent .
docker run -v $HOME/.kube/config:/root/.kube/config patchpulse-agent
```

### In Kubernetes

The agent runs as a Deployment with a ServiceAccount. See Helm charts for deployment.

## Environment Variables

- `BACKEND_URL`: Backend API URL (default: `http://backend:8000`)
- `API_TOKEN`: JWT token for authentication (optional for MVP)
- `KUBECONFIG`: Path to kubeconfig file (for local dev)

## What It Collects

- **Deployments**: Replica counts, availability
- **Pods**: Restart counts
- **Nodes**: Ready status
- **Events**: Warning events (real-time watch)

## Collection Frequency

- **Events**: Real-time (streaming watch)
- **Resource Snapshots**: Every 5 minutes
- **Backend Sync**: Every 30 seconds (batched)

## RBAC Requirements

The agent requires the following permissions:
- `get`, `list`, `watch` on `deployments`, `pods`, `nodes`, `events`
- Read-only access to namespaces

See `helm/agent/templates/rbac.yaml` for the ServiceAccount and RoleBinding.

