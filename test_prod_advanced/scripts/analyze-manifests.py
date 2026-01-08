#!/usr/bin/env python3
"""
Analyze Kubernetes manifests using PatchPulse policy engine.
This script simulates what PatchPulse would detect without needing a live cluster.
"""

import sys
import os
import yaml
import json
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "app" / "backend"))

from models import ChangeEvent, ClusterSignal
from policy_engine import evaluate_policy, registry

def read_yaml_file(file_path):
    """Read and parse YAML file."""
    with open(file_path, 'r') as f:
        return yaml.safe_load(f)

def create_diff_hunk_from_manifest(file_path, manifest):
    """Create a diff hunk representation from a manifest."""
    # Convert manifest to YAML string
    yaml_str = yaml.dump(manifest, default_flow_style=False)
    
    # Create a diff-like representation (all additions since it's a new file)
    lines = yaml_str.split('\n')
    diff_lines = ['+ ' + line for line in lines if line.strip()]
    
    return {
        "file": file_path,
        "hunk": '\n'.join(diff_lines)
    }

def analyze_manifest(manifest_path):
    """Analyze a single manifest file."""
    print(f"\n{'='*80}")
    print(f"📄 Analyzing: {manifest_path.name}")
    print(f"{'='*80}\n")
    
    try:
        manifest = read_yaml_file(manifest_path)
        
        # Create a change event (simulating a new deployment)
        change_event = ChangeEvent(
            source="test",
            repo="test-repo",
            sha="test-sha",
            branch="main",
            files=[str(manifest_path)],
            diff_hunks=[create_diff_hunk_from_manifest(str(manifest_path), manifest)]
        )
        
        # Create some cluster signals (simulating current cluster state)
        cluster_signals = [
            ClusterSignal(
                kind="Node",
                name="node-1",
                namespace="",
                metric="cpu_usage",
                value=85.0,
                signal_metadata={}
            ),
            ClusterSignal(
                kind="Pod",
                name="existing-pod",
                namespace="production",
                metric="restart_count",
                value=3,
                signal_metadata={}
            )
        ]
        
        # Evaluate policy
        result = evaluate_policy(change_event, cluster_signals, mode="enforce")
        
        # Display results
        risk_score = result["risk_score"]
        allowed = result["allowed"]
        guardrails = result["guardrails_triggered"]
        reasons = result["reasons"]
        
        # Risk level
        if risk_score >= 80:
            risk_level = "🔴 CRITICAL"
            emoji = "🚫"
        elif risk_score >= 60:
            risk_level = "🟠 HIGH"
            emoji = "⚠️"
        elif risk_score >= 40:
            risk_level = "🟡 MEDIUM"
            emoji = "⚠️"
        else:
            risk_level = "🟢 LOW"
            emoji = "✅"
        
        print(f"{emoji} Risk Score: {risk_score}/100 ({risk_level})")
        print(f"Decision: {'🚫 BLOCKED' if not allowed else '✅ ALLOWED'}")
        print(f"Mode: {result['mode'].upper()}")
        
        if guardrails:
            print(f"\n📋 Guardrails Triggered ({len(guardrails)}):")
            for gr in guardrails:
                severity_emoji = "🔴" if gr.severity >= 70 else "🟠" if gr.severity >= 50 else "🟡"
                print(f"  {severity_emoji} [{gr.id}] Severity: {gr.severity}/100")
                print(f"     Message: {gr.message}")
                if gr.evidence:
                    print(f"     Evidence: {', '.join(gr.evidence)}")
        
        if reasons:
            print(f"\n📝 Reasons:")
            for reason in reasons:
                print(f"  • {reason}")
        
        if result.get("ai_analysis"):
            ai = result["ai_analysis"]
            print(f"\n🤖 AI Analysis:")
            print(f"  Confidence: {ai.get('confidence', 0):.1%}")
            if ai.get("analysis"):
                print(f"  Analysis: {ai['analysis'][:200]}...")
            if ai.get("recommendations"):
                print(f"  Recommendations:")
                for rec in ai["recommendations"][:3]:
                    print(f"    • {rec}")
        
        return {
            "file": str(manifest_path),
            "risk_score": risk_score,
            "allowed": allowed,
            "guardrails_count": len(guardrails),
            "guardrails": guardrails
        }
        
    except Exception as e:
        print(f"❌ Error analyzing {manifest_path}: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    """Main function."""
    print("🚀 PatchPulse Manifest Analysis")
    print("=" * 80)
    print("Analyzing Kubernetes manifests for security, availability, and cost issues...")
    print("=" * 80)
    
    # Get manifests directory
    manifests_dir = Path(__file__).parent.parent / "manifests"
    
    if not manifests_dir.exists():
        print(f"❌ Manifests directory not found: {manifests_dir}")
        return 1
    
    # Find all YAML files
    manifest_files = sorted(manifests_dir.glob("*.yaml"))
    
    if not manifest_files:
        print(f"❌ No YAML files found in {manifests_dir}")
        return 1
    
    print(f"\n📦 Found {len(manifest_files)} manifest(s) to analyze\n")
    
    results = []
    total_risk = 0
    blocked_count = 0
    guardrails_total = 0
    
    # Analyze each manifest
    for manifest_file in manifest_files:
        result = analyze_manifest(manifest_file)
        if result:
            results.append(result)
            total_risk += result["risk_score"]
            if not result["allowed"]:
                blocked_count += 1
            guardrails_total += result["guardrails_count"]
    
    # Summary
    print(f"\n{'='*80}")
    print("📊 SUMMARY")
    print(f"{'='*80}\n")
    
    print(f"Total Manifests Analyzed: {len(results)}")
    print(f"🚫 Blocked: {blocked_count}")
    print(f"✅ Allowed: {len(results) - blocked_count}")
    print(f"📋 Total Guardrails Triggered: {guardrails_total}")
    
    if results:
        avg_risk = total_risk / len(results)
        print(f"📈 Average Risk Score: {avg_risk:.1f}/100")
        
        # Top issues
        all_guardrails = []
        for r in results:
            all_guardrails.extend(r["guardrails"])
        
        if all_guardrails:
            # Sort by severity
            all_guardrails.sort(key=lambda x: x.severity, reverse=True)
            print(f"\n🔴 Top Issues Detected:")
            for gr in all_guardrails[:5]:
                print(f"  • [{gr.id}] {gr.message} (Severity: {gr.severity}/100)")
    
    print(f"\n{'='*80}")
    print("✅ Analysis Complete!")
    print(f"{'='*80}\n")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())




