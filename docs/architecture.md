# PatchPulse Architecture

## Overview

PatchPulse is a pre-flight risk analysis and guardrail enforcement system for Kubernetes deployments. It analyzes infrastructure changes and cluster signals to produce risk scores and enforce policies before changes are applied.

## System Components

### 1. Backend (FastAPI)
- **Location**: `/backend`
- **Purpose**: Control plane API, policy engine, decision storage
- **Tech**: Python 3.11+, FastAPI, SQLAlchemy, PostgreSQL/SQLite
- **Key Responsibilities**:
  - Receive change events from Git integrations
  - Receive cluster signals from agent
  - Evaluate policies and compute risk scores
  - Store decisions with audit logs
  - Serve API for UI and integrations

### 2. Agent (Go)
- **Location**: `/agent`
- **Purpose**: In-cluster Kubernetes event collector and resource snapshotter
- **Tech**: Go 1.21+, Kubernetes client-go
- **Key Responsibilities**:
  - Watch Kubernetes events (Deployments, Pods, Nodes)
  - Periodically snapshot resource states
  - Send summaries to backend via authenticated API
  - Run with least-privilege RBAC

### 3. Git Integrations
- **Location**: `/integrations/git`
- **Purpose**: Fetch and parse PR/MR diffs
- **Tech**: Python, GitHub API, GitLab API
- **Key Responsibilities**:
  - Poll or webhook-receive PR/MR events
  - Fetch diff content
  - Parse Helm values.yaml and K8s YAML manifests
  - Create ChangeEvent objects

### 4. Slack Integration
- **Location**: `/integrations/slack`
- **Purpose**: Notifications and interactive approvals
- **Tech**: Python, Slack SDK
- **Key Responsibilities**:
  - Post risk reports to Slack channels
  - Include interactive buttons for approval/denial
  - Handle button callbacks

### 5. UI
- **Location**: `/ui`
- **Purpose**: Minimal web interface for risk reports
- **Tech**: HTML/CSS/JS (vanilla or minimal framework)
- **Key Responsibilities**:
  - Display recent decisions
  - Show detailed risk analysis with evidence
  - Link to diff hunks and cluster signals

## Data Flow

```
Git PR/MR → Git Integration → Backend (ChangeEvent)
K8s Cluster → Agent → Backend (ClusterSignal)
Backend → Policy Engine → Decision
Decision → Slack Integration → Slack Notification
Decision → UI → Web Display
```

## Internal Models

### ChangeEvent
```python
{
  "source": "github|gitlab",
  "repo": "org/repo",
  "sha": "commit_sha",
  "pr_number": 123,
  "files": ["path/to/file.yaml"],
  "diff_hunks": [{"file": "...", "hunk": "..."}],
  "timestamp": "2024-01-01T00:00:00Z"
}
```

### ClusterSignal
```python
{
  "kind": "deployment|pod|node|event",
  "namespace": "default",
  "name": "service-name",
  "metric": "cpu_usage|memory_usage|restart_count|...",
  "value": 85.5,
  "timestamp": "2024-01-01T00:00:00Z"
}
```

### Decision
```python
{
  "change_event_id": "uuid",
  "risk_score": 75,
  "reasons": ["Removed resource limits", "High CPU usage detected"],
  "guardrails_triggered": [
    {"id": "no_limits", "severity": 50, "message": "..."}
  ],
  "mode": "advisory|enforce",
  "allowed": true|false,
  "evidence_refs": ["diff_hunk_1", "signal_1"]
}
```

## Policy Engine

- Registry-based guardrail system
- Each guardrail is a Python function that returns:
  - `id`: unique identifier
  - `severity`: 0-100 weight
  - `message`: human-readable explanation
  - `evidence`: list of evidence references
- Risk score = sum(severity * weight) + modifiers
- Modifiers apply for critical namespaces/services

## Security

- Agent uses ServiceAccount with minimal RBAC
- Agent ↔ Backend: JWT with rotation (or mTLS)
- Backend stores secrets in K8s secrets
- All decisions audited with full context
- No secrets in code or config files

## Deployment

- Local: `docker-compose up`
- Kubernetes: Helm charts for agent and backend
- Backend requires PostgreSQL and Redis (optional)
- Agent runs as DaemonSet or Deployment

