#!/bin/bash
# Deploy problematic configurations to demonstrate PatchPulse capabilities

set -e

echo "🚨 Deploying problematic Kubernetes configurations..."
echo "This script demonstrates various issues that PatchPulse will detect and prevent."
echo ""

# Create namespace
kubectl create namespace production --dry-run=client -o yaml | kubectl apply -f -

echo "📦 Deploying problematic manifests..."

# Deploy all problematic configurations
kubectl apply -f manifests/01-problematic-deployment.yaml
kubectl apply -f manifests/02-unsafe-service.yaml
kubectl apply -f manifests/03-resource-hog.yaml
kubectl apply -f manifests/04-insecure-configmap.yaml
kubectl apply -f manifests/05-network-issues.yaml
kubectl apply -f manifests/06-hpa-disabled.yaml
kubectl apply -f manifests/07-old-image.yaml
kubectl apply -f manifests/08-missing-monitoring.yaml

echo ""
echo "✅ All problematic configurations deployed!"
echo ""
echo "🔍 PatchPulse should now detect:"
echo "  • Security vulnerabilities (privileged containers, root user)"
echo "  • Resource issues (missing limits, excessive requests)"
echo "  • High availability problems (single replica, no HPA)"
echo "  • Configuration issues (hardcoded secrets, debug mode)"
echo "  • Network security (overly permissive policies)"
echo "  • Missing monitoring (no probes, no metrics)"
echo ""
echo "📊 Check PatchPulse dashboard to see risk analysis!"

