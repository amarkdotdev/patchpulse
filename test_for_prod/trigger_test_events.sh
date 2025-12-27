#!/bin/bash
set -e

echo "🎯 Triggering test events..."

BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"

# Test 1: Create a risky deployment change event
echo "📝 Creating risky change event (removing resource limits)..."

TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

curl -X POST "${BACKEND_URL}/api/v1/change-events" \
  -H "Content-Type: application/json" \
  -d "{
    \"source\": \"github\",
    \"repo\": \"test/production-app\",
    \"sha\": \"abc123def456\",
    \"pr_number\": 42,
    \"branch\": \"remove-limits\",
    \"files\": [\"k8s/deployment.yaml\"],
    \"diff_hunks\": [
      {
        \"file\": \"k8s/deployment.yaml\",
        \"hunk\": \"@@ -15,7 +15,6 @@ spec:\\n       containers:\\n       - name: app\\n         image: myapp:v1.0.0\\n-        resources:\\n-          limits:\\n-            cpu: 500m\\n-            memory: 512Mi\\n         ports:\\n         - containerPort: 8080\"
      }
    ],
    \"timestamp\": \"${TIMESTAMP}\"
  }" | python3 -m json.tool

echo ""
echo "📊 Creating cluster signals..."

# Create high CPU usage signal
SIGNAL_TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

curl -X POST "${BACKEND_URL}/api/v1/cluster-signals" \
  -H "Content-Type: application/json" \
  -d "[
    {
      \"kind\": \"deployment\",
      \"namespace\": \"production\",
      \"name\": \"production-app\",
      \"metric\": \"cpu_usage\",
      \"value\": 85.5,
      \"timestamp\": \"${SIGNAL_TIMESTAMP}\"
    },
    {
      \"kind\": \"pod\",
      \"namespace\": \"production\",
      \"name\": \"production-app-abc123\",
      \"metric\": \"restart_count\",
      \"value\": 8,
      \"timestamp\": \"${SIGNAL_TIMESTAMP}\"
    }
  ]" | python3 -m json.tool

echo ""
echo "✅ Test events created!"
echo ""
echo "View decisions at: ${BACKEND_URL}/api/v1/decisions"
echo "View UI at: ${BACKEND_URL}/ui"

