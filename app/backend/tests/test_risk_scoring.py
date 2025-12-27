"""Tests for risk scoring logic."""

import pytest
from datetime import datetime
from models import ChangeEvent, ClusterSignal
from policy_engine import calculate_risk_score, evaluate_policy


def test_risk_score_low():
    """Test low risk score calculation."""
    change_event = ChangeEvent(
        source="github",
        repo="test/repo",
        sha="abc123",
        files=["deployment.yaml"],
        diff_hunks=[],
        timestamp=datetime.utcnow()
    )
    
    guardrail_results = [
        type('GuardrailResult', (), {
            'severity': 10,
            'evidence': []
        })()
    ]
    
    score = calculate_risk_score(guardrail_results, change_event)
    assert 0 <= score <= 30


def test_risk_score_medium():
    """Test medium risk score calculation."""
    change_event = ChangeEvent(
        source="github",
        repo="test/repo",
        sha="abc123",
        files=["deployment.yaml"],
        diff_hunks=[],
        timestamp=datetime.utcnow()
    )
    
    guardrail_results = [
        type('GuardrailResult', (), {
            'severity': 40,
            'evidence': []
        })()
    ]
    
    score = calculate_risk_score(guardrail_results, change_event)
    assert 30 < score <= 60


def test_risk_score_high():
    """Test high risk score calculation."""
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
    assert 60 < score <= 100


def test_risk_score_capped_at_100():
    """Test that risk score is capped at 100."""
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
            'severity': 100,
            'evidence': []
        })()
    ]
    
    score = calculate_risk_score(guardrail_results, change_event)
    assert score == 100

