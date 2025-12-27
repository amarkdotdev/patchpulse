# PatchPulse Threat Model

## Overview

This document identifies key security threats and mitigations for PatchPulse.

## Threat Categories

### 1. Unauthorized Access to Backend API

**Threat**: Attacker gains access to backend API and can:
- View sensitive change events and decisions
- Manipulate decisions
- Access cluster signals

**Mitigations**:
- JWT authentication between agent and backend (or mTLS)
- API token rotation
- Network policies to restrict access
- RBAC for Kubernetes API access

**Status**: MVP uses optional API tokens. Production should enforce authentication.

### 2. Agent Privilege Escalation

**Threat**: Compromised agent pod could:
- Access sensitive cluster resources
- Modify deployments
- Exfiltrate cluster data

**Mitigations**:
- Least-privilege RBAC (read-only access)
- Agent runs in dedicated namespace
- Network policies restrict agent communication
- Regular security audits of agent code

**Status**: MVP implements read-only RBAC. Agent cannot modify resources.

### 3. Git Integration Token Compromise

**Threat**: Stolen GitHub/GitLab token allows:
- Access to private repositories
- Modification of PRs
- Exfiltration of code

**Mitigations**:
- Tokens stored in Kubernetes secrets (not in code)
- Tokens with minimal scopes (read-only for PRs)
- Regular token rotation
- Monitor for unusual API activity

**Status**: MVP uses environment variables. Production should use K8s secrets.

### 4. Policy Engine Bypass

**Threat**: Attacker manipulates policy evaluation to:
- Allow risky changes
- Bypass guardrails
- Modify risk scores

**Mitigations**:
- Policy engine code in read-only container
- Audit logs for all policy evaluations
- Policy versioning and signatures
- Fail-closed mode for policy engine errors

**Status**: MVP logs all decisions. Policy code is immutable in container.

### 5. Database Compromise

**Threat**: Database access allows:
- Viewing all change events and decisions
- Modifying audit logs
- Data exfiltration

**Mitigations**:
- Database encryption at rest
- Network encryption in transit
- Database access restricted to backend only
- Regular backups
- Database credentials in secrets

**Status**: MVP uses PostgreSQL with basic auth. Production should use encryption.

### 6. Slack Integration Abuse

**Threat**: Compromised Slack integration could:
- Send malicious notifications
- Approve risky changes via buttons
- Exfiltrate decision data

**Mitigations**:
- Slack token in secrets
- Verify Slack request signatures
- Rate limit button callbacks
- Audit all button interactions

**Status**: MVP uses Slack SDK. Production should verify request signatures.

### 7. Supply Chain Attacks

**Threat**: Compromised dependencies could:
- Inject malicious code
- Exfiltrate data
- Modify behavior

**Mitigations**:
- Pin dependency versions
- Regular dependency updates
- Scan for vulnerabilities
- Use signed container images
- Verify image signatures

**Status**: MVP pins versions. Production should scan and sign images.

### 8. Denial of Service

**Threat**: Attacker could:
- Overwhelm backend with requests
- Exhaust database connections
- Crash agent with malformed data

**Mitigations**:
- Rate limiting on API endpoints
- Request size limits
- Connection pooling
- Resource limits on containers
- Circuit breakers

**Status**: MVP has basic resource limits. Production should add rate limiting.

## Security Controls Summary

| Control | MVP Status | Production Requirement |
|---------|-----------|----------------------|
| Authentication | Optional tokens | Required JWT/mTLS |
| RBAC | Read-only agent | Enforced, audited |
| Secrets Management | Env vars | Kubernetes secrets |
| Encryption | In transit (TLS) | At rest + in transit |
| Audit Logging | All decisions | Immutable, tamper-proof |
| Image Signing | Not implemented | Required |
| Rate Limiting | Not implemented | Required |
| Network Policies | Not implemented | Required |

## Recommendations

1. **Immediate (Pre-Production)**:
   - Enforce authentication between agent and backend
   - Move all secrets to Kubernetes secrets
   - Enable database encryption at rest
   - Add rate limiting

2. **Short-term**:
   - Implement network policies
   - Add image signing
   - Set up security scanning
   - Enable audit log immutability

3. **Long-term**:
   - Policy engine code signing
   - Zero-trust networking
   - Regular penetration testing
   - Security incident response plan

## Compliance Considerations

- **SOC 2**: Audit logs, access controls, encryption
- **GDPR**: Data minimization, retention policies
- **PCI DSS**: If handling payment data (not applicable for MVP)

## Incident Response

If a security incident is detected:

1. Isolate affected components
2. Preserve audit logs
3. Notify security team
4. Rotate all credentials
5. Review and update threat model

