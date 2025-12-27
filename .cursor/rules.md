# PatchPulse Cursor Rules

## North Star
PatchPulse prevents incidents by analyzing changes + cluster signals and enforcing pre-flight guardrails.
Everything we build must directly support: Risk scoring, Explainability, Guardrails, Integrations, Security, Ship-ability.

## Product Constraints (MVP)
- Kubernetes-first. Local dev via docker-compose.
- Integrations: Git (GitHub + GitLab minimal) and Slack.
- Output must be explainable with evidence: exact diff hunks + cluster signals.
- Advisory mode first; enforcement mode second.
- 5 guardrails minimum in MVP.

## Engineering Standards
- Prefer boring tech: FastAPI, SQLAlchemy, Pydantic, PostgreSQL/SQLite, Prometheus metrics.
- Code must run end-to-end. No "TODO: implement" in core paths.
- Every service must have:
  - health endpoint
  - structured JSON logs
  - config via env vars
  - container build
- Provide Makefile targets:
  - make lint, make test, make run, make build, make docker-up, make helm-install, make helm-uninstall

## Security Standards
- No secrets in repo.
- Use Kubernetes secrets and local `.env` (gitignored).
- Least privilege RBAC for agent: only what it needs (events, deployments, namespaces, nodes read-only).
- Auth between agent <-> backend must be explicit:
  - either mTLS or signed token with rotation
- Audit log every decision:
  - who/what triggered it, inputs, outputs, policy version

## Architecture Rules
- Keep components decoupled:
  - agent collects and POSTs summaries (not raw noisy firehose unless sampled)
  - backend stores and evaluates
  - integrations fetch diffs and map to “change events”
- Use a normalized internal model:
  - ChangeEvent (source, repo, sha, files, diff hunks, timestamp)
  - ClusterSignal (kind, namespace, metric/event, value, timestamp)
  - Decision (risk_score, reasons[], guardrails_triggered[], mode, allow/deny, evidence refs)
- Evidence references must always point to stored artifacts.

## Policy Engine Rules
- Start simple: Python guardrail functions with a registry.
- Must be structured and extensible:
  - guardrail returns: {id, severity, message, evidence[]}
- Risk score must be deterministic:
  - sum weighted severities + modifiers for critical namespaces/services
- Must support "advisory" vs "enforce" modes using config.

## Testing Rules
- Unit tests:
  - diff parser
  - risk scoring
  - each guardrail
- Integration test:
  - simulate ChangeEvent + ClusterSignal -> Decision
- Add sample fixtures:
  - manifests, diffs, signals

## UX Rules
- Slack message must show:
  - risk score (0-100)
  - top reasons (max 5)
  - evidence links/refs
  - recommended action (canary, rollback plan, add limits, etc.)
- UI can be minimal but must show:
  - recent decisions
  - detail view with evidence

## Documentation Rules
- docs/quickstart.md: local + k8s install
- docs/demo.md: exact steps for the demo scenario
- docs/threat-model.md: key threats + mitigations
- docs/runbooks.md: common ops tasks

## Delivery Discipline
- Always update docs when behavior changes.
- If you make an assumption, write it in docs/assumptions.md.
- Prefer fewer features that work end-to-end over many half-features.
