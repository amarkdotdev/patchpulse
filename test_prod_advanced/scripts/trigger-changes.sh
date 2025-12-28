#!/bin/bash
# Trigger various changes to demonstrate PatchPulse change analysis

set -e

echo "🔄 Triggering changes to demonstrate PatchPulse capabilities..."
echo ""

# Change 1: Remove resource limits (HIGH RISK)
echo "1️⃣ Removing resource limits from critical-api-service..."
kubectl patch deployment critical-api-service -n production --type='json' -p='[
  {"op": "remove", "path": "/spec/template/spec/containers/0/resources/limits"}
]' || echo "⚠️  Deployment might not exist yet"

# Change 2: Scale down to 0 replicas (HIGH RISK)
echo "2️⃣ Scaling down critical service to 0 replicas..."
kubectl scale deployment critical-api-service -n production --replicas=0 || echo "⚠️  Deployment might not exist yet"

# Change 3: Change to privileged container
echo "3️⃣ Enabling privileged mode..."
kubectl patch deployment critical-api-service -n production --type='json' -p='[
  {"op": "replace", "path": "/spec/template/spec/containers/0/securityContext/privileged", "value": true}
]' || echo "⚠️  Deployment might not exist yet"

# Change 4: Add hardcoded secret
echo "4️⃣ Adding hardcoded secret to environment..."
kubectl patch deployment critical-api-service -n production --type='json' -p='[
  {"op": "add", "path": "/spec/template/spec/containers/0/env/-", "value": {"name": "DB_PASSWORD", "value": "secret123"}}
]' || echo "⚠️  Deployment might not exist yet"

# Change 5: Remove readiness probe
echo "5️⃣ Removing readiness probe..."
kubectl patch deployment critical-api-service -n production --type='json' -p='[
  {"op": "remove", "path": "/spec/template/spec/containers/0/readinessProbe"}
]' || echo "⚠️  Deployment might not exist yet"

# Change 6: Change image to old version
echo "6️⃣ Downgrading to old image version..."
kubectl set image deployment/critical-api-service -n production api=nginx:1.18 || echo "⚠️  Deployment might not exist yet"

echo ""
echo "✅ Changes triggered!"
echo ""
echo "🔍 PatchPulse should detect and analyze all these changes:"
echo "  • Resource limit removal → HIGH RISK"
echo "  • Replica scaling to 0 → HIGH RISK (service unavailability)"
echo "  • Privileged container → CRITICAL SECURITY RISK"
echo "  • Hardcoded secrets → SECURITY RISK"
echo "  • Missing readiness probe → OPERATIONAL RISK"
echo "  • Old image version → SECURITY VULNERABILITY RISK"
echo ""
echo "📊 Check PatchPulse dashboard for detailed analysis!"


