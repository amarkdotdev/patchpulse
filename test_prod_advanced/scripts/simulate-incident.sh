#!/bin/bash
# Simulate a production incident scenario

set -e

echo "🚨 Simulating production incident scenario..."
echo ""

# Scenario: Developer accidentally removes resource limits and scales down
echo "📝 Scenario: Developer makes dangerous changes via GitOps"
echo ""

# Create a "PR" that removes limits
echo "1️⃣ Creating change event: Removing resource limits..."
cat > /tmp/dangerous-change.yaml <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: critical-api-service
spec:
  template:
    spec:
      containers:
      - name: api
        # REMOVED: resources.limits
        resources:
          requests:
            memory: "100Mi"
EOF

echo "2️⃣ Simulating cluster signals (high CPU usage)..."
# In real scenario, PatchPulse agent would detect this
echo "   • CPU usage: 95%"
echo "   • Memory usage: 88%"
echo "   • Pod restarts: 5 in last hour"

echo ""
echo "3️⃣ PatchPulse Analysis:"
echo "   🔴 RISK SCORE: 85/100"
echo "   🚫 DECISION: BLOCKED"
echo "   📋 REASONS:"
echo "      • Missing resource limits can cause node exhaustion"
echo "      • High CPU usage detected in cluster"
echo "      • Recent pod restarts indicate instability"
echo "      • Critical service - requires careful review"
echo ""
echo "✅ Incident PREVENTED by PatchPulse!"
echo ""
echo "💡 AI Recommendations:"
echo "   • Add resource limits: memory: 512Mi, cpu: 500m"
echo "   • Investigate high CPU usage before deploying"
echo "   • Consider scaling horizontally instead"
echo "   • Review recent pod restart patterns"


