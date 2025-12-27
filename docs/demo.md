# PatchPulse Demo Scenario

This guide walks through the complete demo scenario: creating a risky PR, having PatchPulse analyze it, and seeing the risk report.

## Prerequisites

- PatchPulse running (local or Kubernetes)
- GitHub repository with sample manifests
- Slack workspace configured (optional)

## Demo Steps

### 1. Prepare Sample Service

Create a sample Kubernetes deployment manifest:

```yaml
# samples/critical-service/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: critical-service
  namespace: production
spec:
  replicas: 3
  selector:
    matchLabels:
      app: critical-service
  template:
    metadata:
      labels:
        app: critical-service
    spec:
      containers:
      - name: app
        image: myapp:v1.0.0
        resources:
          limits:
            cpu: 500m
            memory: 512Mi
          requests:
            cpu: 200m
            memory: 256Mi
        ports:
        - containerPort: 8080
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: critical-service-hpa
  namespace: production
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: critical-service
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

Commit and push to your repository.

### 2. Create Risky PR

Create a new branch and make risky changes:

```bash
git checkout -b risky-changes
```

Edit `samples/critical-service/deployment.yaml`:

```yaml
# Remove resource limits
apiVersion: apps/v1
kind: Deployment
metadata:
  name: critical-service
  namespace: production
spec:
  replicas: 3
  selector:
    matchLabels:
      app: critical-service
  template:
    metadata:
      labels:
        app: critical-service
    spec:
      containers:
      - name: app
        image: myapp:latest  # Changed to latest
        # Resources removed!
        ports:
        - containerPort: 8080
# HPA removed entirely
```

Create PR:

```bash
git add samples/critical-service/deployment.yaml
git commit -m "Remove resource limits and HPA for performance testing"
git push origin risky-changes
# Create PR via GitHub UI
```

### 3. PatchPulse Detects Change

The Git poller (running every 60 seconds) will:
1. Detect the new PR
2. Fetch the diff
3. Send ChangeEvent to backend
4. Backend evaluates policy
5. Creates Decision with risk score

### 4. View Risk Analysis

#### Via API

```bash
# List recent decisions
curl http://localhost:8000/api/v1/decisions | jq

# Get specific decision
curl http://localhost:8000/api/v1/decisions/{decision_id} | jq
```

Expected response:
```json
{
  "id": "...",
  "change_event_id": "...",
  "risk_score": 85,
  "reasons": [
    "Resource limits removed or missing",
    "HorizontalPodAutoscaler removed",
    "Image tag is 'latest' (not recommended for production)"
  ],
  "guardrails_triggered": [
    {
      "id": "no_resource_limits",
      "severity": 50,
      "message": "Resource limits removed or missing",
      "evidence": ["File: samples/critical-service/deployment.yaml"]
    },
    {
      "id": "hpa_disabled",
      "severity": 40,
      "message": "HorizontalPodAutoscaler removed",
      "evidence": ["File: samples/critical-service/deployment.yaml"]
    },
    {
      "id": "image_tag_latest",
      "severity": 25,
      "message": "Image tag is 'latest' (not recommended for production)",
      "evidence": ["File: samples/critical-service/deployment.yaml"]
    }
  ],
  "mode": "advisory",
  "allowed": true,
  "evidence_refs": ["File: samples/critical-service/deployment.yaml"]
}
```

#### Via UI

1. Open http://localhost:8000/ui
2. See decision in list with risk score 85/100 (High)
3. Click to view details
4. See all guardrails triggered and evidence

#### Via Slack (if configured)

Slack message will show:
- Risk score: 🔴 85/100 (Critical)
- Top issues listed
- Guardrails triggered
- Recommended action: "⚠️ Consider canary deployment or rollback plan before merging."
- Interactive buttons: View Details, Approve, Deny

### 5. Test Enforcement Mode

Change policy mode to enforce:

```bash
# Update backend config
export POLICY_MODE=enforce
docker-compose restart backend

# Or in Kubernetes
kubectl set env deployment/patchpulse-backend POLICY_MODE=enforce
```

Create another risky PR. This time, with risk score > 70, the decision will have `"allowed": false`.

### 6. Fix the Issues

Update the PR to address guardrails:

```yaml
# Add back resources
resources:
  limits:
    cpu: 500m
    memory: 512Mi
  requests:
    cpu: 200m
    memory: 256Mi

# Use specific image tag
image: myapp:v1.0.1

# Add back HPA
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
...
```

PatchPulse will re-evaluate and show lower risk score.

## Expected Outcomes

1. **Advisory Mode**: All decisions logged, but changes allowed
2. **Enforce Mode**: High-risk changes blocked (allowed=false)
3. **Evidence**: All guardrails cite specific diff hunks
4. **Explainability**: Clear reasons and recommended actions

## Troubleshooting

- **No decisions appearing**: Check git-poller logs, verify GitHub token
- **Agent not collecting signals**: Check agent logs, verify RBAC permissions
- **Slack not posting**: Check Slack token and channel configuration

## Sample Files

See `samples/` directory for:
- `critical-service/deployment.yaml` - Sample deployment
- `pr-diffs/` - Sample PR diff files for testing

