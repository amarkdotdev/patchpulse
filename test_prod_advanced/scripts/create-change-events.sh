#!/bin/bash
# Create change events via API to demonstrate PatchPulse detection

set -e

API_BASE="http://localhost:8000/api/v1"
BACKEND_URL="$API_BASE"

echo "🚀 Creating change events to demonstrate PatchPulse capabilities..."
echo ""

# First, sign up a test user
echo "1️⃣ Creating test user..."
SIGNUP_RESPONSE=$(curl -s -X POST "$BACKEND_URL/auth/signup" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@patchpulse.io",
    "password": "testpass123",
    "full_name": "Test User",
    "company": "PatchPulse"
  }')

echo "$SIGNUP_RESPONSE" | jq -r '.message // .detail // .' 2>/dev/null || echo "$SIGNUP_RESPONSE"

# Login to get token
echo ""
echo "2️⃣ Logging in..."
LOGIN_RESPONSE=$(curl -s -X POST "$BACKEND_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@patchpulse.io",
    "password": "testpass123"
  }')

TOKEN=$(echo "$LOGIN_RESPONSE" | jq -r '.access_token // .token // ""' 2>/dev/null)

if [ -z "$TOKEN" ] || [ "$TOKEN" = "null" ]; then
  echo "⚠️  Could not get token. Response: $LOGIN_RESPONSE"
  echo "Continuing without auth (if API allows)..."
  AUTH_HEADER=""
else
  echo "✅ Got auth token"
  AUTH_HEADER="Authorization: Bearer $TOKEN"
fi

echo ""
echo "3️⃣ Creating change event for problematic deployment..."

# Read the manifest and create a diff
MANIFEST_CONTENT=$(cat manifests/01-problematic-deployment.yaml)

# Create change event simulating a PR that adds this problematic deployment
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%S")
CHANGE_EVENT=$(cat <<EOF
{
  "source": "github",
  "repo": "my-org/production-configs",
  "sha": "abc123def456",
  "branch": "main",
  "pr_number": 123,
  "files": ["manifests/01-problematic-deployment.yaml"],
  "diff_hunks": [
    {
      "file": "manifests/01-problematic-deployment.yaml",
      "hunk": "+ apiVersion: apps/v1\n+ kind: Deployment\n+ metadata:\n+   name: critical-api-service\n+   namespace: production\n+ spec:\n+   replicas: 1\n+   template:\n+     spec:\n+       containers:\n+       - name: api\n+         image: nginx:latest\n+         resources:\n+           requests:\n+             memory: \"100Mi\"\n+         securityContext:\n+           privileged: true\n+           runAsUser: 0\n+         env:\n+         - name: API_KEY\n+           value: \"hardcoded-secret-key-12345\""
    }
  ],
  "timestamp": "$TIMESTAMP"
}
EOF
)

if [ -n "$AUTH_HEADER" ]; then
  RESPONSE=$(curl -s -X POST "$BACKEND_URL/change-events" \
    -H "Content-Type: application/json" \
    -H "$AUTH_HEADER" \
    -d "$CHANGE_EVENT")
else
  RESPONSE=$(curl -s -X POST "$BACKEND_URL/change-events" \
    -H "Content-Type: application/json" \
    -d "$CHANGE_EVENT")
fi

echo "$RESPONSE" | jq '.' 2>/dev/null || echo "$RESPONSE"

echo ""
echo "4️⃣ Creating change event for removing resource limits..."

TIMESTAMP2=$(date -u +"%Y-%m-%dT%H:%M:%S")
REMOVE_LIMITS_EVENT=$(cat <<EOF
{
  "source": "github",
  "repo": "my-org/production-configs",
  "sha": "def456ghi789",
  "branch": "main",
  "pr_number": 124,
  "files": ["manifests/01-problematic-deployment.yaml"],
  "diff_hunks": [
    {
      "file": "manifests/01-problematic-deployment.yaml",
      "hunk": "- resources:\n-   limits:\n-     memory: \"512Mi\"\n-     cpu: \"500m\"\n+ resources:\n+   requests:\n+     memory: \"100Mi\""
    }
  ],
  "timestamp": "$TIMESTAMP2"
}
EOF
)

if [ -n "$AUTH_HEADER" ]; then
  RESPONSE2=$(curl -s -X POST "$BACKEND_URL/change-events" \
    -H "Content-Type: application/json" \
    -H "$AUTH_HEADER" \
    -d "$REMOVE_LIMITS_EVENT")
else
  RESPONSE2=$(curl -s -X POST "$BACKEND_URL/change-events" \
    -H "Content-Type: application/json" \
    -d "$REMOVE_LIMITS_EVENT")
fi

echo "$RESPONSE2" | jq '.' 2>/dev/null || echo "$RESPONSE2"

echo ""
echo "✅ Change events created!"
echo ""
echo "📊 Check the dashboard at http://localhost:8000/dashboard to see the analysis!"

