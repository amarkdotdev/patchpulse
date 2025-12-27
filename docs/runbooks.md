# PatchPulse Runbooks

Common operational tasks and troubleshooting guides.

## Health Checks

### Backend Health

```bash
# Check health endpoint
curl http://localhost:8000/health

# Expected: {"status": "healthy", "timestamp": "..."}

# Check metrics
curl http://localhost:8000/metrics

# Check database connection
kubectl exec -it deployment/patchpulse-backend -- python -c "from database import engine; engine.connect()"
```

### Agent Health

```bash
# Check agent logs
kubectl logs -l app.kubernetes.io/component=agent --tail=50

# Check agent can access cluster
kubectl exec -it deployment/patchpulse-agent -- /app/agent --version

# Verify RBAC
kubectl auth can-i get deployments --as=system:serviceaccount:default:patchpulse-agent
```

### Git Poller Health

```bash
# Check poller logs
docker-compose logs git-poller

# Test GitHub API access
curl -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/user
```

## Common Issues

### Issue: No Decisions Being Created

**Symptoms**: UI shows no decisions, API returns empty list.

**Diagnosis**:
1. Check git-poller is running and has valid tokens
2. Verify backend is receiving change events
3. Check backend logs for errors

**Resolution**:
```bash
# Check git-poller logs
docker-compose logs git-poller | grep -i error

# Test backend API
curl -X POST http://localhost:8000/api/v1/change-events \
  -H "Content-Type: application/json" \
  -d '{"source": "github", "repo": "test/repo", "sha": "abc123", "files": [], "diff_hunks": [], "timestamp": "2024-01-01T00:00:00Z"}'

# Check database
kubectl exec -it deployment/patchpulse-backend -- python -c "from database import SessionLocal; from models import ChangeEventDB; db = SessionLocal(); print(db.query(ChangeEventDB).count())"
```

### Issue: Agent Not Collecting Signals

**Symptoms**: No cluster signals in database, agent logs show errors.

**Diagnosis**:
1. Check agent RBAC permissions
2. Verify agent can access Kubernetes API
3. Check backend connectivity

**Resolution**:
```bash
# Check RBAC
kubectl describe role patchpulse-agent
kubectl describe rolebinding patchpulse-agent

# Test agent connectivity
kubectl exec -it deployment/patchpulse-agent -- wget -O- http://patchpulse-backend:8000/health

# Check agent service account
kubectl get serviceaccount patchpulse-agent
```

### Issue: High Risk Scores for Safe Changes

**Symptoms**: Low-risk changes getting high risk scores.

**Diagnosis**:
1. Review guardrail logic
2. Check for false positives
3. Verify cluster signals are accurate

**Resolution**:
```bash
# Get decision details
curl http://localhost:8000/api/v1/decisions/{decision_id} | jq

# Review guardrails triggered
# Adjust guardrail severity if needed
# Update policy_engine.py
```

### Issue: Slack Notifications Not Sending

**Symptoms**: Decisions created but no Slack messages.

**Diagnosis**:
1. Check Slack token validity
2. Verify bot is in channel
3. Check Slack integration logs

**Resolution**:
```bash
# Test Slack API
curl -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  https://slack.com/api/auth.test

# Check channel access
curl -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  "https://slack.com/api/conversations.list"

# Verify webhook URL (if using)
curl -X POST $SLACK_WEBHOOK_URL \
  -H "Content-Type: application/json" \
  -d '{"text": "Test message"}'
```

## Maintenance Tasks

### Database Backup

```bash
# PostgreSQL backup
kubectl exec -it deployment/patchpulse-backend-postgres -- \
  pg_dump -U patchpulse patchpulse > backup.sql

# Restore
kubectl exec -i deployment/patchpulse-backend-postgres -- \
  psql -U patchpulse patchpulse < backup.sql
```

### Rotate API Tokens

```bash
# Generate new token
NEW_TOKEN=$(openssl rand -hex 32)

# Update agent
kubectl set env deployment/patchpulse-agent API_TOKEN=$NEW_TOKEN

# Update backend (if needed)
kubectl set env deployment/patchpulse-backend AGENT_TOKEN=$NEW_TOKEN
```

### Update Policy Mode

```bash
# Switch to enforce mode
kubectl set env deployment/patchpulse-backend POLICY_MODE=enforce

# Switch back to advisory
kubectl set env deployment/patchpulse-backend POLICY_MODE=advisory

# Verify
curl http://localhost:8000/api/v1/decisions | jq '.[0].mode'
```

### Clean Old Data

```bash
# Delete decisions older than 30 days (via API or direct DB)
kubectl exec -it deployment/patchpulse-backend -- python <<EOF
from database import SessionLocal
from models import DecisionDB
from datetime import datetime, timedelta
db = SessionLocal()
cutoff = datetime.utcnow() - timedelta(days=30)
count = db.query(DecisionDB).filter(DecisionDB.created_at < cutoff).delete()
db.commit()
print(f"Deleted {count} old decisions")
EOF
```

## Scaling

### Scale Backend

```bash
# Increase replicas
kubectl scale deployment patchpulse-backend --replicas=3

# Check load balancing
kubectl get endpoints patchpulse-backend
```

### Scale Agent

```bash
# Agent can run multiple instances (they don't conflict)
kubectl scale deployment patchpulse-agent --replicas=2
```

## Monitoring

### Key Metrics

- `patchpulse_decisions_total`: Total decisions made
- `patchpulse_risk_score`: Risk score distribution
- `patchpulse_request_duration_seconds`: API latency

### Alerts

Set up alerts for:
- Backend health check failures
- Agent not sending signals (no signals in 10 minutes)
- High error rate in API
- Database connection failures

## Disaster Recovery

1. **Backend Failure**: Restart deployment, restore from backup if needed
2. **Agent Failure**: Restart deployment, signals will resume
3. **Database Failure**: Restore from backup, restart backend
4. **Complete Cluster Loss**: Restore from backups, redeploy via Helm

## Support

For issues not covered here:
1. Check logs: `kubectl logs -l app.kubernetes.io/component=backend`
2. Review [Threat Model](threat-model.md) for security issues
3. Check [Assumptions](assumptions.md) for design decisions

