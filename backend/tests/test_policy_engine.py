"""Tests for policy engine and guardrails."""

import pytest
from datetime import datetime
from models import ChangeEvent, ClusterSignal
from policy_engine import (
    registry, calculate_risk_score, evaluate_policy,
    check_no_resource_limits, check_hpa_disabled,
    check_high_cpu_usage, check_pod_restarts,
    check_critical_service_modification, check_image_tag_latest
)


def test_check_no_resource_limits():
    """Test guardrail for missing resource limits."""
    change_event = ChangeEvent(
        source="github",
        repo="test/repo",
        sha="abc123",
        files=["deployment.yaml"],
        diff_hunks=[{
            "file": "deployment.yaml",
            "hunk": "- limits:\n  cpu: 500m\n  memory: 512Mi"
        }],
        timestamp=datetime.utcnow()
    )
    
    result = check_no_resource_limits(change_event, [])
    assert result is not None
    assert result.id == "no_resource_limits"
    assert result.severity == 50


def test_check_hpa_disabled():
    """Test guardrail for HPA removal."""
    change_event = ChangeEvent(
        source="github",
        repo="test/repo",
        sha="abc123",
        files=["hpa.yaml"],
        diff_hunks=[{
            "file": "hpa.yaml",
            "hunk": "- kind: HorizontalPodAutoscaler\n  name: my-hpa"
        }],
        timestamp=datetime.utcnow()
    )
    
    result = check_hpa_disabled(change_event, [])
    assert result is not None
    assert result.id == "hpa_disabled"


def test_check_high_cpu_usage():
    """Test guardrail for high CPU usage."""
    change_event = ChangeEvent(
        source="github",
        repo="test/repo",
        sha="abc123",
        files=[],
        diff_hunks=[],
        timestamp=datetime.utcnow()
    )
    
    signals = [
        ClusterSignal(
            kind="deployment",
            namespace="default",
            name="my-service",
            metric="cpu_usage",
            value=85.5,
            timestamp=datetime.utcnow()
        )
    ]
    
    result = check_high_cpu_usage(change_event, signals)
    assert result is not None
    assert result.id == "high_cpu_usage"
    assert result.severity == 30


def test_check_pod_restarts():
    """Test guardrail for excessive pod restarts."""
    change_event = ChangeEvent(
        source="github",
        repo="test/repo",
        sha="abc123",
        files=[],
        diff_hunks=[],
        timestamp=datetime.utcnow()
    )
    
    signals = [
        ClusterSignal(
            kind="pod",
            namespace="default",
            name="my-pod",
            metric="restart_count",
            value=10.0,
            timestamp=datetime.utcnow()
        )
    ]
    
    result = check_pod_restarts(change_event, signals)
    assert result is not None
    assert result.id == "excessive_restarts"
    assert result.severity == 35


def test_check_critical_service_modification():
    """Test guardrail for critical service modification."""
    change_event = ChangeEvent(
        source="github",
        repo="test/repo",
        sha="abc123",
        files=["api-server.yaml"],
        diff_hunks=[{
            "file": "api-server.yaml",
            "hunk": "kind: Deployment\nname: api-server\nreplicas: 1"
        }],
        timestamp=datetime.utcnow()
    )
    
    result = check_critical_service_modification(change_event, [])
    assert result is not None
    assert result.id == "critical_service_modification"
    assert result.severity == 60


def test_check_image_tag_latest():
    """Test guardrail for latest image tag."""
    change_event = ChangeEvent(
        source="github",
        repo="test/repo",
        sha="abc123",
        files=["deployment.yaml"],
        diff_hunks=[{
            "file": "deployment.yaml",
            "hunk": "image: myapp:latest"
        }],
        timestamp=datetime.utcnow()
    )
    
    result = check_image_tag_latest(change_event, [])
    assert result is not None
    assert result.id == "image_tag_latest"
    assert result.severity == 25


def test_calculate_risk_score():
    """Test risk score calculation."""
    change_event = ChangeEvent(
        source="github",
        repo="test/repo",
        sha="abc123",
        files=["production/deployment.yaml"],
        diff_hunks=[],
        timestamp=datetime.utcnow()
    )
    
    guardrail_results = [
        type('GuardrailResult', (), {
            'severity': 50,
            'evidence': []
        })(),
        type('GuardrailResult', (), {
            'severity': 30,
            'evidence': []
        })()
    ]
    
    score = calculate_risk_score(guardrail_results, change_event)
    # Base score: 50 + 30 = 80
    # Modifier for production namespace: +20
    # Total: 100 (capped)
    assert score == 100


def test_evaluate_policy_advisory():
    """Test policy evaluation in advisory mode."""
    change_event = ChangeEvent(
        source="github",
        repo="test/repo",
        sha="abc123",
        files=["deployment.yaml"],
        diff_hunks=[{
            "file": "deployment.yaml",
            "hunk": "- limits:\n  cpu: 500m"
        }],
        timestamp=datetime.utcnow()
    )
    
    signals = [
        ClusterSignal(
            kind="deployment",
            namespace="default",
            name="my-service",
            metric="cpu_usage",
            value=85.0,
            timestamp=datetime.utcnow()
        )
    ]
    
    result = evaluate_policy(change_event, signals, mode="advisory")
    
    assert result["risk_score"] > 0
    assert result["mode"] == "advisory"
    assert result["allowed"] is True  # Advisory mode always allows
    assert len(result["reasons"]) > 0
    assert len(result["guardrails_triggered"]) > 0


def test_evaluate_policy_enforce():
    """Test policy evaluation in enforce mode."""
    change_event = ChangeEvent(
        source="github",
        repo="test/repo",
        sha="abc123",
        files=["production/deployment.yaml"],
        diff_hunks=[{
            "file": "production/deployment.yaml",
            "hunk": "- limits:\n  cpu: 500m\n- kind: HorizontalPodAutoscaler"
        }],
        timestamp=datetime.utcnow()
    )
    
    signals = [
        ClusterSignal(
            kind="deployment",
            namespace="production",
            name="critical-service",
            metric="cpu_usage",
            value=90.0,
            timestamp=datetime.utcnow()
        )
    ]
    
    result = evaluate_policy(change_event, signals, mode="enforce")
    
    assert result["risk_score"] > 70
    assert result["mode"] == "enforce"
    assert result["allowed"] is False  # Should block high risk
    assert len(result["guardrails_triggered"]) >= 2

