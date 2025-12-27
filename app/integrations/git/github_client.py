"""GitHub integration for fetching PR diffs."""

import os
import requests
from typing import List, Dict, Optional
from datetime import datetime


class GitHubClient:
    """Client for GitHub API."""
    
    def __init__(self, token: Optional[str] = None):
        self.token = token or os.getenv("GITHUB_TOKEN")
        self.base_url = "https://api.github.com"
        self.headers = {
            "Accept": "application/vnd.github.v3.diff",
            "User-Agent": "PatchPulse/1.0"
        }
        if self.token:
            self.headers["Authorization"] = f"token {self.token}"
    
    def get_pr_diff(self, owner: str, repo: str, pr_number: int) -> Optional[str]:
        """Get PR diff."""
        url = f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}"
        response = requests.get(url, headers=self.headers)
        if response.status_code != 200:
            return None
        
        pr_data = response.json()
        diff_url = pr_data.get("diff_url")
        if not diff_url:
            return None
        
        diff_response = requests.get(diff_url, headers=self.headers)
        if diff_response.status_code != 200:
            return None
        
        return diff_response.text
    
    def get_pr_files(self, owner: str, repo: str, pr_number: int) -> List[Dict]:
        """Get list of files changed in PR."""
        url = f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}/files"
        response = requests.get(url, headers=self.headers)
        if response.status_code != 200:
            return []
        
        files = []
        for file_data in response.json():
            files.append({
                "path": file_data.get("filename"),
                "status": file_data.get("status"),  # added, removed, modified
                "additions": file_data.get("additions", 0),
                "deletions": file_data.get("deletions", 0),
                "patch": file_data.get("patch", "")
            })
        
        return files
    
    def list_open_prs(self, owner: str, repo: str) -> List[Dict]:
        """List open PRs."""
        url = f"{self.base_url}/repos/{owner}/{repo}/pulls"
        params = {"state": "open", "sort": "updated", "direction": "desc"}
        response = requests.get(url, headers=self.headers, params=params)
        if response.status_code != 200:
            return []
        
        return response.json()
    
    def parse_diff_to_hunks(self, diff_text: str) -> List[Dict[str, str]]:
        """Parse diff text into hunks."""
        hunks = []
        current_file = None
        current_hunk = []
        
        for line in diff_text.split("\n"):
            if line.startswith("diff --git") or line.startswith("---") or line.startswith("+++"):
                if line.startswith("---"):
                    # Extract filename
                    parts = line.split()
                    if len(parts) > 1:
                        current_file = parts[1].lstrip("a/").lstrip("b/")
                continue
            
            if line.startswith("@@"):
                # Save previous hunk
                if current_file and current_hunk:
                    hunks.append({
                        "file": current_file,
                        "hunk": "\n".join(current_hunk)
                    })
                current_hunk = [line]
                continue
            
            if current_hunk is not None:
                current_hunk.append(line)
        
        # Save last hunk
        if current_file and current_hunk:
            hunks.append({
                "file": current_file,
                "hunk": "\n".join(current_hunk)
            })
        
        return hunks


def create_change_event_from_pr(owner: str, repo: str, pr_data: Dict, client: GitHubClient) -> Dict:
    """Create ChangeEvent from GitHub PR."""
    pr_number = pr_data["number"]
    sha = pr_data["head"]["sha"]
    branch = pr_data["head"]["ref"]
    
    files = client.get_pr_files(owner, repo, pr_number)
    file_paths = [f["path"] for f in files]
    
    # Collect all patches into hunks
    all_hunks = []
    for file_info in files:
        if file_info.get("patch"):
            all_hunks.append({
                "file": file_info["path"],
                "hunk": file_info["patch"]
            })
    
    return {
        "source": "github",
        "repo": f"{owner}/{repo}",
        "sha": sha,
        "pr_number": pr_number,
        "branch": branch,
        "files": file_paths,
        "diff_hunks": all_hunks,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

