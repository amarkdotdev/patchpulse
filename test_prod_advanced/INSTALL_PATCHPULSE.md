# Installing PatchPulse for Advanced Test Scenario

## Quick Installation

### Option 1: Using Docker Compose (Recommended for Testing)

```bash
# Clone the repository
git clone <your-repo-url>
cd sre_agent

# Start PatchPulse
docker compose up -d

# Verify installation
curl http://localhost:8000/health
```

### Option 2: Using Helm (Production)

```bash
# Add PatchPulse Helm repository
helm repo add patchpulse https://charts.patchpulse.io
helm repo update

# Install PatchPulse
helm install patchpulse patchpulse/patchpulse \
  --namespace patchpulse \
  --create-namespace \
  --set backend.deepseekApiKey=your-api-key-here
```

## Configuration

### 1. Set API Key

Create `.env` file:
```bash
DEEPSEEK_API_KEY=your-deepseek-api-key-here
JWT_SECRET_KEY=your-jwt-secret-key-here
```

### 2. Configure Policy Mode

Edit `app/backend/main.py` or set environment variable:
```bash
POLICY_MODE=enforce  # or "advisory" for warnings only
```

### 3. Deploy Agent to Cluster

```bash
# Apply agent deployment
kubectl apply -f helm/patchpulse-agent/templates/

# Verify agent is running
kubectl get pods -n patchpulse
```

## Access Points

- **Dashboard:** http://localhost:8000/dashboard
- **API:** http://localhost:8000/api/v1
- **API Docs:** http://localhost:8000/docs

## Testing the Installation

```bash
# Test signup
curl -X POST http://localhost:8000/api/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"testpass123","full_name":"Test User"}'

# Test change event
curl -X POST http://localhost:8000/api/v1/change-events \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "source": "github",
    "repo": "my-repo",
    "sha": "abc123",
    "files": ["deployment.yaml"],
    "diff_hunks": [{"file": "deployment.yaml", "hunk": "- resources:\n+ # resources removed"}]
  }'
```

## Next Steps

1. Deploy problematic configurations: `./scripts/deploy-problems.sh`
2. Trigger changes: `./scripts/trigger-changes.sh`
3. View results in dashboard: http://localhost:8000/dashboard


