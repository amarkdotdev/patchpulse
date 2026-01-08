#!/usr/bin/env python3
"""Comprehensive test suite for PatchPulse backend."""

import sys
import os
import subprocess
import json
import time
from datetime import datetime
from typing import Dict, List, Tuple

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app', 'backend'))

# Test results
test_results: List[Dict] = []
total_tests = 0
passed_tests = 0
failed_tests = 0


def log_test(name: str, status: str, message: str = "", details: str = ""):
    """Log a test result."""
    global total_tests, passed_tests, failed_tests
    total_tests += 1
    if status == "PASS":
        passed_tests += 1
    else:
        failed_tests += 1
    
    result = {
        "name": name,
        "status": status,
        "message": message,
        "details": details,
        "timestamp": datetime.now().isoformat()
    }
    test_results.append(result)
    
    status_symbol = "✅" if status == "PASS" else "❌"
    print(f"{status_symbol} {name}: {message}")
    if details:
        print(f"   {details}")


def test_imports():
    """Test that all critical modules can be imported."""
    print("\n=== Testing Imports ===")
    
    modules = [
        ("models", "models"),
        ("database", "database"),
        ("policy_engine", "policy_engine"),
        ("main", "main"),
        ("auth", "auth"),
        ("admission_webhook", "admission_webhook"),
        ("policy_bundles", "policy_bundles"),
        ("evidence_pack", "evidence_pack"),
        ("signal_collector_v2", "signal_collector_v2"),
        ("sbom_verification", "sbom_verification"),
        ("multi_tenancy", "multi_tenancy"),
    ]
    
    for module_name, import_name in modules:
        try:
            __import__(import_name)
            log_test(f"Import {module_name}", "PASS", "Module imported successfully")
        except Exception as e:
            log_test(f"Import {module_name}", "FAIL", f"Import failed: {str(e)}")


def test_database_connection():
    """Test database connection and initialization."""
    print("\n=== Testing Database ===")
    
    try:
        from database import init_db, get_db, engine
        
        # Test engine creation
        if engine:
            log_test("Database Engine", "PASS", "Engine created successfully")
        else:
            log_test("Database Engine", "FAIL", "Engine is None")
        
        # Test init_db
        try:
            init_db()
            log_test("Database Initialization", "PASS", "Database initialized successfully")
        except Exception as e:
            log_test("Database Initialization", "FAIL", f"Init failed: {str(e)}")
        
        # Test get_db
        try:
            db_gen = get_db()
            db = next(db_gen)
            db.close()
            log_test("Database Session", "PASS", "Session created and closed successfully")
        except Exception as e:
            log_test("Database Session", "FAIL", f"Session failed: {str(e)}")
            
    except Exception as e:
        log_test("Database Setup", "FAIL", f"Database setup failed: {str(e)}")


def test_models():
    """Test Pydantic models."""
    print("\n=== Testing Models ===")
    
    try:
        from models import ChangeEvent, ClusterSignal, Decision
        from datetime import datetime
        
        # Test ChangeEvent
        try:
            event = ChangeEvent(
                source="test",
                repo="test/repo",
                sha="abc123",
                files=["test.yaml"],
                diff_hunks=[],
                timestamp=datetime.utcnow()
            )
            log_test("ChangeEvent Model", "PASS", "Model created successfully")
        except Exception as e:
            log_test("ChangeEvent Model", "FAIL", f"Model creation failed: {str(e)}")
        
        # Test ClusterSignal
        try:
            signal = ClusterSignal(
                kind="deployment",
                namespace="default",
                name="test",
                metric="cpu",
                value=50.0,
                timestamp=datetime.utcnow()
            )
            log_test("ClusterSignal Model", "PASS", "Model created successfully")
        except Exception as e:
            log_test("ClusterSignal Model", "FAIL", f"Model creation failed: {str(e)}")
            
    except Exception as e:
        log_test("Models Import", "FAIL", f"Models import failed: {str(e)}")


def test_policy_engine():
    """Test policy engine functionality."""
    print("\n=== Testing Policy Engine ===")
    
    try:
        from policy_engine import evaluate_policy, calculate_risk_score
        from models import ChangeEvent, ClusterSignal
        from datetime import datetime
        
        # Create test change event
        change_event = ChangeEvent(
            source="test",
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
                name="test",
                metric="cpu_usage",
                value=85.0,
                timestamp=datetime.utcnow()
            )
        ]
        
        # Test policy evaluation
        try:
            result = evaluate_policy(change_event, signals, mode="advisory")
            if "risk_score" in result and "allowed" in result:
                log_test("Policy Evaluation", "PASS", f"Risk score: {result['risk_score']}")
            else:
                log_test("Policy Evaluation", "FAIL", "Result missing required fields")
        except Exception as e:
            log_test("Policy Evaluation", "FAIL", f"Evaluation failed: {str(e)}")
            
    except Exception as e:
        log_test("Policy Engine Import", "FAIL", f"Import failed: {str(e)}")


def test_admission_webhook():
    """Test admission webhook functionality."""
    print("\n=== Testing Admission Webhook ===")
    
    try:
        from admission_webhook import analyze_resource
        
        # Test resource analysis
        test_resource = {
            "kind": "Deployment",
            "metadata": {"name": "test"},
            "spec": {
                "template": {
                    "spec": {
                        "containers": [{
                            "image": "nginx:latest",
                            "securityContext": {"privileged": True}
                        }]
                    }
                }
            }
        }
        
        try:
            result = analyze_resource(test_resource, mode="advisory")
            if "risk_score" in result:
                log_test("Admission Webhook Analysis", "PASS", f"Risk score: {result['risk_score']}")
            else:
                log_test("Admission Webhook Analysis", "FAIL", "Result missing risk_score")
        except Exception as e:
            log_test("Admission Webhook Analysis", "FAIL", f"Analysis failed: {str(e)}")
            
    except Exception as e:
        log_test("Admission Webhook Import", "FAIL", f"Import failed: {str(e)}")


def test_sbom_verification():
    """Test SBOM verification."""
    print("\n=== Testing SBOM Verification ===")
    
    try:
        from sbom_verification import SBOMVerifier
        
        verifier = SBOMVerifier()
        
        # Test image verification
        try:
            result = verifier.verify_image("nginx:latest")
            if "risk_score" in result:
                log_test("SBOM Verification", "PASS", f"Risk score: {result['risk_score']}")
            else:
                log_test("SBOM Verification", "FAIL", "Result missing risk_score")
        except Exception as e:
            log_test("SBOM Verification", "FAIL", f"Verification failed: {str(e)}")
            
    except Exception as e:
        log_test("SBOM Verifier Import", "FAIL", f"Import failed: {str(e)}")


def test_api_endpoints():
    """Test API endpoints if backend is running."""
    print("\n=== Testing API Endpoints ===")
    
    import httpx
    
    base_url = "http://localhost:8000"
    
    # Test health endpoint
    try:
        response = httpx.get(f"{base_url}/health", timeout=5.0)
        if response.status_code == 200:
            data = response.json()
            log_test("Health Endpoint", "PASS", f"Status: {data.get('status', 'unknown')}")
        else:
            log_test("Health Endpoint", "FAIL", f"Status code: {response.status_code}")
    except httpx.ConnectError:
        log_test("Health Endpoint", "SKIP", "Backend not running")
    except Exception as e:
        log_test("Health Endpoint", "FAIL", f"Request failed: {str(e)}")
    
    # Test root endpoint
    try:
        response = httpx.get(f"{base_url}/", timeout=5.0)
        if response.status_code == 200:
            log_test("Root Endpoint", "PASS", "Root endpoint accessible")
        else:
            log_test("Root Endpoint", "FAIL", f"Status code: {response.status_code}")
    except httpx.ConnectError:
        log_test("Root Endpoint", "SKIP", "Backend not running")
    except Exception as e:
        log_test("Root Endpoint", "FAIL", f"Request failed: {str(e)}")


def run_pytest_tests():
    """Run pytest unit tests."""
    print("\n=== Running Pytest Unit Tests ===")
    
    test_dir = os.path.join(os.path.dirname(__file__), "app", "backend", "tests")
    
    if not os.path.exists(test_dir):
        log_test("Pytest Tests", "SKIP", "Test directory not found")
        return
    
    try:
        result = subprocess.run(
            ["python3", "-m", "pytest", test_dir, "-v", "--tb=short"],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=os.path.dirname(__file__)
        )
        
        if result.returncode == 0:
            log_test("Pytest Tests", "PASS", "All unit tests passed")
        else:
            log_test("Pytest Tests", "FAIL", f"Some tests failed", result.stdout[-500:])
    except subprocess.TimeoutExpired:
        log_test("Pytest Tests", "FAIL", "Tests timed out")
    except FileNotFoundError:
        log_test("Pytest Tests", "SKIP", "pytest not installed")
    except Exception as e:
        log_test("Pytest Tests", "FAIL", f"Test execution failed: {str(e)}")


def generate_report():
    """Generate test report."""
    print("\n" + "="*60)
    print("TEST REPORT")
    print("="*60)
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {failed_tests}")
    print(f"Success Rate: {(passed_tests/total_tests*100):.1f}%" if total_tests > 0 else "N/A")
    print("="*60)
    
    # Write JSON report
    report_file = "test_report.json"
    with open(report_file, "w") as f:
        json.dump({
            "summary": {
                "total": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "success_rate": (passed_tests/total_tests*100) if total_tests > 0 else 0
            },
            "tests": test_results,
            "timestamp": datetime.now().isoformat()
        }, f, indent=2)
    
    print(f"\nDetailed report saved to: {report_file}")
    
    # Print failed tests
    failed = [t for t in test_results if t["status"] == "FAIL"]
    if failed:
        print("\nFailed Tests:")
        for test in failed:
            print(f"  - {test['name']}: {test['message']}")


def main():
    """Run all tests."""
    print("="*60)
    print("PATCHPULSE FULL TEST SUITE")
    print("="*60)
    print(f"Started at: {datetime.now().isoformat()}")
    
    # Run all test categories
    test_imports()
    test_database_connection()
    test_models()
    test_policy_engine()
    test_admission_webhook()
    test_sbom_verification()
    test_api_endpoints()
    run_pytest_tests()
    
    # Generate report
    generate_report()
    
    # Exit with appropriate code
    sys.exit(0 if failed_tests == 0 else 1)


if __name__ == "__main__":
    main()


