#!/bin/bash
set -e

echo "🚀 Setting up local Kubernetes cluster for PatchPulse testing..."

# Check if k3d is installed
if ! command -v k3d &> /dev/null; then
    echo "❌ k3d is not installed. Installing..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        brew install k3d
    else
        echo "Please install k3d from https://k3d.io"
        exit 1
    fi
fi

# Check if cluster already exists
if k3d cluster list | grep -q patchpulse-test; then
    echo "⚠️  Cluster 'patchpulse-test' already exists. Deleting..."
    k3d cluster delete patchpulse-test
fi

# Create cluster
echo "📦 Creating k3d cluster 'patchpulse-test'..."
k3d cluster create patchpulse-test \
    --port "8000:80@loadbalancer" \
    --port "8443:443@loadbalancer" \
    --wait

# Wait for cluster to be ready
echo "⏳ Waiting for cluster to be ready..."
kubectl wait --for=condition=ready node --all --timeout=120s

# Set kubeconfig
export KUBECONFIG=$(k3d kubeconfig write patchpulse-test)

echo "✅ Cluster is ready!"
echo ""
echo "Next steps:"
echo "  1. Run: ./deploy_patchpulse.sh"
echo "  2. Run: ./trigger_test_events.sh"
echo ""
echo "To access cluster:"
echo "  kubectl get nodes"

