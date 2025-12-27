"""GitLab integration for fetching MR diffs."""

import os
import requests
from typing import List, Dict, Optional
from datetime import datetime


class GitLabClient:
    """Client for GitLab API."""
    
    def __init__(self, token: Optional[str] = None, base_url: Optional[str] = None):
        self.token = token or os.getenv("GITLAB_TOKEN")
        self.base_url = base_url or os.getenv("GITLAB_URL", "https://gitlab.com/api/v4")
        self.headers = {
            "User-Agent": "PatchPulse/1.0"
        }
        if self.token:
            self.headers["PRIVATE-TOKEN"] = self.token
    
    def get_mr_diff(self, project_id: str, mr_iid: int) -> Optional[str]:
        """Get MR diff."""
        url = f"{self.base_url}/projects/{project_id}/merge_requests/{mr_iid}/diffs"
        response = requests.get(url, headers=self.headers)
        if response.status_code != 200:
            return None
        
        diffs = response.json()
        # Combine all diffs into single text
        diff_text = ""
        for diff in diffs.get("diffs", []):
            diff_text += diff.get("diff", "")
        
        return diff_text
    
    def get_mr_changes(self, project_id: str, mr_iid: int) -> List[Dict]:
        """Get list of files changed in MR."""
        url = f"{self.base_url}/projects/{project_id}/merge_requests/{mr_iid}/changes"
        response = requests.get(url, headers=self.headers)
        if response.status_code != 200:
            return []
        
        changes = response.json()
        files = []
        for change in changes.get("changes", []):
            files.append({
                "path": change.get("new_path") or change.get("old_path"),
                "status": "added" if change.get("new_file") else "removed" if change.get("deleted_file") else "modified",
                "diff": change.get("diff", "")
            })
        
        return files
    
    def list_open_mrs(self, project_id: str) -> List[Dict]:
        """List open MRs."""
        url = f"{self.base_url}/projects/{project_id}/merge_requests"
        params = {"state": "opened", "order_by": "updated_at", "sort": "desc"}
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
                    parts = line.split()
                    if len(parts) > 1:
                        current_file = parts[1].lstrip("a/").lstrip("b/")
                continue
            
            if line.startswith("@@"):
                if current_file and current_hunk:
                    hunks.append({
                        "file": current_file,
                        "hunk": "\n".join(current_hunk)
                    })
                current_hunk = [line]
                continue
            
            if current_hunk is not None:
                current_hunk.append(line)
        
        if current_file and current_hunk:
            hunks.append({
                "file": current_file,
                "hunk": "\n".join(current_hunk)
            })
        
        return hunks


def create_change_event_from_mr(project_id: str, mr_data: Dict, client: GitLabClient) -> Dict:
    """Create ChangeEvent from GitLab MR."""
    mr_iid = mr_data["iid"]
    sha = mr_data["sha"]
    branch = mr_data["source_branch"]
    
    files = client.get_mr_changes(project_id, mr_iid)
    file_paths = [f["path"] for f in files]
    
    all_hunks = []
    for file_info in files:
        if file_info.get("diff"):
            all_hunks.append({
                "file": file_info["path"],
                "hunk": file_info["diff"]
            })
    
    return {
        "source": "gitlab",
        "repo": project_id,  # GitLab uses project ID
        "sha": sha,
        "pr_number": mr_iid,  # Using pr_number field for MR IID
        "branch": branch,
        "files": file_paths,
        "diff_hunks": all_hunks,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

