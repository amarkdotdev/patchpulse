#!/bin/bash
# Comprehensive test suite for PatchPulse in Kind cluster

set -e

NAMESPACE="patchpulse-test"
CONTEXT="kind-patchpulse-test"
BACKEND_URL="http://localhost:8001"

echo "🧪 PatchPulse Kind Cluster Test Suite"
echo "======================================"
echo ""

# Setup port-forward
echo "Setting up port-forward..."
kubectl port-forward svc/backend 8001:8000 -n $NAMESPACE --context $CONTEXT > /dev/null 2>&1 &
PF_PID=$!
sleep 5

cleanup() {
    echo ""
    echo "Cleaning up..."
    kill $PF_PID 2>/dev/null || true
}
trap cleanup EXIT

# Test functions
test_health() {
    echo "✅ TEST 1: Health Check"
    curl -s $BACKEND_URL/health | jq -r '.status' | grep -q "healthy" && echo "   PASS" || echo "   FAIL"
}

test_api_info() {
    echo "✅ TEST 2: API Info"
    curl -s $BACKEND_URL/api | jq -r '.name' | grep -q "PatchPulse" && echo "   PASS" || echo "   FAIL"
}

test_decisions() {
    echo "✅ TEST 3: Decisions Endpoint"
    DECISIONS=$(curl -s $BACKEND_URL/api/v1/decisions?limit=5)
    echo "$DECISIONS" | jq -e 'type == "array"' > /dev/null && echo "   PASS" || echo "   FAIL"
}

test_analytics() {
    echo "✅ TEST 4: Analytics"
    curl -s $BACKEND_URL/api/v1/analytics/summary | jq -e '.total_decisions != null' > /dev/null && echo "   PASS" || echo "   FAIL"
}

test_integrations() {
    echo "✅ TEST 5: Integrations"
    curl -s $BACKEND_URL/api/v1/integrations | jq -e '.teams != null' > /dev/null && echo "   PASS" || echo "   FAIL"
}

test_export() {
    echo "✅ TEST 6: Export"
    curl -s "$BACKEND_URL/api/v1/export/decisions?format=json&limit=2" | jq -e 'type == "array"' > /dev/null && echo "   PASS" || echo "   FAIL"
}

test_change_event() {
    echo "✅ TEST 7: Create Change Event"
    TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%S")
    RESPONSE=$(curl -s -X POST "$BACKEND_URL/api/v1/change-events" \
        -H "Content-Type: application/json" \
        -d "{
            \"source\": \"github\",
            \"repo\": \"test/repo\",
            \"sha\": \"test-sha\",
            \"branch\": \"main\",
            \"pr_number\": 1,
            \"files\": [\"test.yaml\"],
            \"diff_hunks\": [{\"file\": \"test.yaml\", \"hunk\": \"+ apiVersion: v1\"}],
            \"timestamp\": \"$TIMESTAMP\"
        }")
    echo "$RESPONSE" | jq -e '.decision_id != null' > /dev/null && echo "   PASS" || echo "   FAIL"
}

test_kubernetes_resources() {
    echo "✅ TEST 8: Kubernetes Resources"
    kubectl get deployment test-app -n $NAMESPACE --context $CONTEXT > /dev/null 2>&1 && echo "   PASS" || echo "   FAIL"
}

test_webhook() {
    echo "✅ TEST 9: Webhook Creation"
    RESPONSE=$(curl -s -X POST "$BACKEND_URL/api/v1/webhooks" \
        -H "Content-Type: application/json" \
        -d '{"url":"https://example.com/webhook","events":["decision_created"]}')
    echo "$RESPONSE" | jq -e '.id != null' > /dev/null && echo "   PASS" || echo "   FAIL"
}

test_audit_log() {
    echo "✅ TEST 10: Audit Log"
    curl -s "$BACKEND_URL/api/v1/audit?limit=5" | jq -e '.entries != null' > /dev/null && echo "   PASS" || echo "   FAIL"
}

# Run all tests
test_health
test_api_info
test_decisions
test_analytics
test_integrations
test_export
test_change_event
test_kubernetes_resources
test_webhook
test_audit_log

echo ""
echo "✅ Test suite complete!"

