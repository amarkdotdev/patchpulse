"""Tests for diff parsing."""

import pytest
from integrations.git.github_client import GitHubClient


def test_parse_diff_to_hunks():
    """Test parsing diff text into hunks."""
    client = GitHubClient()
    
    diff_text = """diff --git a/deployment.yaml b/deployment.yaml
--- a/deployment.yaml
+++ b/deployment.yaml
@@ -5,7 +5,6 @@ spec:
       containers:
       - name: app
         image: myapp:v1.0
-        resources:
-          limits:
-            cpu: 500m
-            memory: 512Mi
+        # Resources removed
         ports:
         - containerPort: 8080
"""
    
    hunks = client.parse_diff_to_hunks(diff_text)
    
    assert len(hunks) > 0
    assert hunks[0]["file"] == "deployment.yaml"
    assert "limits" in hunks[0]["hunk"]
    assert "cpu: 500m" in hunks[0]["hunk"]

