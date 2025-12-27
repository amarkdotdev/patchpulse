#!/bin/bash
set -e

echo "📦 Deploying PatchPulse to test cluster..."

# Set kubeconfig
export KUBECONFIG=$(k3d kubeconfig write patchpulse-test)

# Build and load images into k3d
echo "🔨 Building images..."
cd ..
docker compose build backend agent

echo "📤 Loading images into cluster..."
k3d image import sre_agent-backend:latest -c patchpulse-test
k3d image import sre_agent-agent:latest -c patchpulse-test

# Create namespace
kubectl create namespace patchpulse --dry-run=client -o yaml | kubectl apply -f -

# Deploy backend
echo "🚀 Deploying backend..."
helm install patchpulse-backend ../helm/backend \
    --namespace patchpulse \
    --set image.repository=sre_agent-backend \
    --set image.tag=latest \
    --set image.pullPolicy=Never \
    --set env.DATABASE_URL="postgresql://patchpulse:patchpulse@patchpulse-backend-postgres:5432/patchpulse" \
    --set env.POLICY_MODE=advisory \
    --set service.type=NodePort \
    --set service.nodePort=30080

# Deploy agent
echo "🤖 Deploying agent..."
helm install patchpulse-agent ../helm/agent \
    --namespace patchpulse \
    --set image.repository=sre_agent-agent \
    --set image.tag=latest \
    --set image.pullPolicy=Never \
    --set env.BACKEND_URL="http://patchpulse-backend:8000"

# Wait for deployments
echo "⏳ Waiting for deployments..."
kubectl wait --for=condition=available deployment/patchpulse-backend -n patchpulse --timeout=120s
kubectl wait --for=condition=available deployment/patchpulse-agent -n patchpulse --timeout=120s

# Port forward backend
echo "🔌 Setting up port forwarding..."
kubectl port-forward -n patchpulse svc/patchpulse-backend 8000:8000 &
PORT_FORWARD_PID=$!
echo $PORT_FORWARD_PID > .port_forward_pid

echo "✅ PatchPulse deployed!"
echo ""
echo "Backend: http://localhost:8000"
echo "UI: http://localhost:8000/ui"
echo ""
echo "To stop port forwarding: kill \$(cat .port_forward_pid)"

