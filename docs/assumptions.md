# PatchPulse Assumptions

This document tracks assumptions made during development. Update this when making architectural or behavioral changes.

## Architecture Assumptions

1. **Agent Deployment**: Agent runs as a Deployment (not DaemonSet) - one instance per cluster is sufficient for MVP. Can scale horizontally if needed.

2. **Database**: SQLite for local dev, PostgreSQL for production. Backend auto-detects based on DATABASE_URL.

3. **Authentication**: JWT-based auth between agent and backend (simpler than mTLS for MVP). Token rotation handled via backend API endpoint.

4. **Git Integration**: Polling-based for MVP (no webhooks). Polls every 60 seconds for new PRs/MRs. Can be extended to webhooks later.

5. **Slack Integration**: Uses Slack Web API and interactive buttons. Requires Slack app with bot token. Buttons use callback URLs pointing to backend.

6. **Policy Mode**: Default mode is "advisory" - decisions are logged but not enforced. Enforcement mode blocks changes via Git status checks or admission webhooks (future).

7. **Risk Score Range**: 0-100, where:
   - 0-30: Low risk
   - 31-60: Medium risk
   - 61-80: High risk
   - 81-100: Critical risk

8. **Critical Namespaces**: Hardcoded list for MVP: `["kube-system", "production", "prod"]`. Can be configured via env var.

9. **Evidence Storage**: Evidence (diff hunks, signals) stored in database as JSON. No separate artifact storage for MVP.

10. **UI Framework**: Vanilla HTML/CSS/JS for MVP. No build step required. Served by FastAPI static files.

11. **Agent Collection Frequency**: 
    - Events: Real-time watch (streaming)
    - Resource snapshots: Every 5 minutes
    - Summary sent to backend: Every 30 seconds (batched)

12. **Guardrail Evaluation**: All guardrails evaluated for every change event. No early exit for MVP.

13. **Diff Parsing**: Supports:
    - Raw Kubernetes YAML manifests
    - Helm values.yaml files
    - Detects removals, additions, modifications
    - Extracts resource types, names, namespaces

14. **Cluster Signal Collection**: Agent collects:
    - Deployment replicas and status
    - Pod restart counts
    - Node conditions
    - Recent events (last 1 hour)

15. **Decision Persistence**: All decisions stored permanently for audit. No TTL for MVP.

16. **API Versioning**: No versioning for MVP. All endpoints under `/api/v1/`.

17. **Error Handling**: Fail-open for MVP (if policy engine fails, allow change with warning). Can be configured to fail-closed.

18. **Observability**: Structured JSON logs to stdout. Prometheus metrics on `/metrics` endpoint. No separate logging infrastructure.

19. **Configuration**: All config via environment variables. No config files except for Helm values.

20. **Testing**: Unit tests use pytest. Integration tests use docker-compose. No e2e tests for MVP.

