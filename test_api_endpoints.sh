#!/bin/bash
# Comprehensive API endpoint testing script

set -e

BASE_URL="http://localhost:8000"
PASSED=0
FAILED=0

echo "============================================================"
echo "PATCHPULSE API ENDPOINT TEST SUITE"
echo "============================================================"
echo ""

test_endpoint() {
    local name=$1
    local method=$2
    local endpoint=$3
    local data=$4
    local expected_status=${5:-200}
    
    echo -n "Testing $name... "
    
    if [ "$method" = "GET" ]; then
        response=$(curl -s -w "\n%{http_code}" "$BASE_URL$endpoint" || echo "000")
    elif [ "$method" = "POST" ]; then
        response=$(curl -s -w "\n%{http_code}" -X POST \
            -H "Content-Type: application/json" \
            -d "$data" \
            "$BASE_URL$endpoint" || echo "000")
    else
        response=$(curl -s -w "\n%{http_code}" -X "$method" "$BASE_URL$endpoint" || echo "000")
    fi
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" = "$expected_status" ]; then
        echo "✅ PASS (Status: $http_code)"
        PASSED=$((PASSED + 1))
        return 0
    else
        echo "❌ FAIL (Expected: $expected_status, Got: $http_code)"
        if [ -n "$body" ]; then
            echo "   Response: $body" | head -c 200
            echo ""
        fi
        FAILED=$((FAILED + 1))
        return 1
    fi
}

# Wait for backend to be ready
echo "Waiting for backend to be ready..."
for i in {1..30}; do
    if curl -s "$BASE_URL/health" > /dev/null 2>&1; then
        echo "✅ Backend is ready"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ Backend not ready after 30 seconds"
        exit 1
    fi
    sleep 1
done

echo ""
echo "=== Testing Core Endpoints ==="
test_endpoint "Health Check" "GET" "/health" "" 200
test_endpoint "Root Endpoint" "GET" "/" "" 200
test_endpoint "Metrics Endpoint" "GET" "/metrics" "" 200
test_endpoint "Dashboard Redirect" "GET" "/dashboard" "" 307

echo ""
echo "=== Testing API Endpoints ==="
test_endpoint "List Decisions" "GET" "/api/v1/decisions" "" 200
test_endpoint "List Change Events" "GET" "/api/v1/change-events" "" 200

echo ""
echo "=== Testing Change Event Creation ==="
CHANGE_EVENT='{
  "source": "test",
  "repo": "test/repo",
  "sha": "abc123",
  "files": ["deployment.yaml"],
  "diff_hunks": [{
    "file": "deployment.yaml",
    "hunk": "- limits:\n  cpu: 500m"
  }]
}'
test_endpoint "Create Change Event" "POST" "/api/v1/change-events" "$CHANGE_EVENT" 200

echo ""
echo "=== Testing Enterprise Features ==="
test_endpoint "Admission Validate" "POST" "/admission/validate" '{"kind":"AdmissionReview"}' 200
test_endpoint "Admission Mutate" "POST" "/admission/mutate" '{"kind":"AdmissionReview"}' 200
test_endpoint "List Policy Bundles" "GET" "/api/v1/policy-bundles" "" 200
test_endpoint "SBOM Verify" "POST" "/api/v1/sbom/verify" '{"image":"nginx:latest"}' 200

echo ""
echo "=== Testing Auth Endpoints ==="
SIGNUP_DATA='{
  "email": "test@example.com",
  "password": "testpassword123",
  "full_name": "Test User"
}'
test_endpoint "User Signup" "POST" "/api/v1/auth/signup" "$SIGNUP_DATA" 200

LOGIN_DATA='{
  "email": "test@example.com",
  "password": "testpassword123"
}'
test_endpoint "User Login" "POST" "/api/v1/auth/login" "$LOGIN_DATA" 200

echo ""
echo "============================================================"
echo "TEST SUMMARY"
echo "============================================================"
echo "Passed: $PASSED"
echo "Failed: $FAILED"
echo "Total: $((PASSED + FAILED))"
echo "============================================================"

if [ $FAILED -eq 0 ]; then
    exit 0
else
    exit 1
fi

