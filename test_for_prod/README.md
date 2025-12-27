# PatchPulse Production Test Environment

This directory contains everything needed to test PatchPulse end-to-end with a local Kubernetes cluster.

## 🎯 Complete Feature Showcase

This test environment demonstrates **all PatchPulse AI-powered features**:

### 🤖 AI-Powered Analysis
- **Risk Scoring**: Hybrid AI + rule-based scoring (0-100) with confidence levels
- **Security Scanning**: AI detects vulnerabilities, privilege escalation, network exposure, secret leaks, RBAC misconfigurations
- **Recommendations**: Actionable, code-level suggestions with examples to fix issues
- **Incident Prediction**: Pattern-based analysis predicting incidents before they happen with probability scores
- **Cost Optimization**: Identifies over-provisioned resources, missing limits, and provides savings estimates

### 🛡️ Guardrails (11 Total)
- Missing resource limits
- Disabled HPA
- High CPU/memory usage
- Excessive pod restarts
- Critical service modifications
- Latest image tags
- Privileged security contexts
- Host network usage
- Missing readiness probes
- Low replica counts
- And more...

### 📊 Real-Time Features
- WebSocket live updates (new decisions appear instantly)
- Cluster signal monitoring
- Risk distribution charts
- Analytics dashboard
- Export functionality
- Search and filtering

### 🔗 Integrations
- GitHub PR analysis
- GitLab MR analysis
- Slack notifications with interactive buttons
- Kubernetes agent with least-privilege RBAC
- REST API for CI/CD integration

### 🔒 Security
- API key protection (zero leakage - never in logs/responses)
- Least-privilege RBAC
- Audit logging
- Response validation
- Rate limiting

## Quick Start

```bash
# 1. Start local cluster (k3d - lightweight, fast)
./setup_cluster.sh

# 2. Deploy PatchPulse
./deploy_patchpulse.sh

# 3. Trigger test events (showcases all features)
./trigger_test_events.sh

# 4. View results in dashboard
open http://localhost:8000/dashboard
```

## Requirements

- Docker Desktop running
- kubectl installed
- k3d installed (`brew install k3d` or see https://k3d.io)

## What Gets Tested

1. **Agent**: Collects cluster signals in real-time
2. **Git Integration**: Detects PR changes and extracts diffs
3. **AI Analysis**: Runs security scans, recommendations, predictions
4. **Policy Engine**: Evaluates with 11 guardrails + AI scoring
5. **Decisions**: Created with full AI insights and displayed in dashboard
6. **Notifications**: Slack integration (if configured)
7. **WebSocket**: Real-time updates to dashboard

