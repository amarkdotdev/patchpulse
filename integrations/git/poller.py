"""Polling service for Git integrations."""

import os
import time
import requests
from typing import Optional
from github_client import GitHubClient, create_change_event_from_pr
from gitlab_client import GitLabClient, create_change_event_from_mr


class GitPoller:
    """Polls Git repositories for new PRs/MRs and sends to backend."""
    
    def __init__(self, backend_url: str):
        self.backend_url = backend_url
        self.github_client = GitHubClient()
        self.gitlab_client = GitLabClient()
        self.processed_prs = set()  # Track processed PRs to avoid duplicates
    
    def send_change_event(self, change_event: dict) -> bool:
        """Send change event to backend."""
        url = f"{self.backend_url}/api/v1/change-events"
        response = requests.post(url, json=change_event)
        return response.status_code == 200
    
    def poll_github(self, owner: str, repo: str):
        """Poll GitHub for new PRs."""
        prs = self.github_client.list_open_prs(owner, repo)
        for pr_data in prs:
            pr_key = f"github:{owner}/{repo}:{pr_data['number']}"
            if pr_key in self.processed_prs:
                continue
            
            try:
                change_event = create_change_event_from_pr(owner, repo, pr_data, self.github_client)
                if self.send_change_event(change_event):
                    self.processed_prs.add(pr_key)
                    print(f"Processed GitHub PR #{pr_data['number']} from {owner}/{repo}")
            except Exception as e:
                print(f"Error processing GitHub PR: {e}")
    
    def poll_gitlab(self, project_id: str):
        """Poll GitLab for new MRs."""
        mrs = self.gitlab_client.list_open_mrs(project_id)
        for mr_data in mrs:
            mr_key = f"gitlab:{project_id}:{mr_data['iid']}"
            if mr_key in self.processed_prs:
                continue
            
            try:
                change_event = create_change_event_from_mr(project_id, mr_data, self.gitlab_client)
                if self.send_change_event(change_event):
                    self.processed_prs.add(mr_key)
                    print(f"Processed GitLab MR !{mr_data['iid']} from {project_id}")
            except Exception as e:
                print(f"Error processing GitLab MR: {e}")
    
    def run(self, poll_interval: int = 60):
        """Run polling loop."""
        github_repos = os.getenv("GITHUB_REPOS", "").split(",")
        gitlab_projects = os.getenv("GITLAB_PROJECTS", "").split(",")
        
        print(f"Starting Git poller (interval: {poll_interval}s)")
        print(f"GitHub repos: {github_repos}")
        print(f"GitLab projects: {gitlab_projects}")
        
        while True:
            # Poll GitHub
            for repo_str in github_repos:
                if not repo_str.strip():
                    continue
                parts = repo_str.strip().split("/")
                if len(parts) == 2:
                    owner, repo = parts
                    self.poll_github(owner, repo)
            
            # Poll GitLab
            for project_id in gitlab_projects:
                if project_id.strip():
                    self.poll_gitlab(project_id.strip())
            
            time.sleep(poll_interval)


if __name__ == "__main__":
    backend_url = os.getenv("BACKEND_URL", "http://localhost:8000")
    poll_interval = int(os.getenv("POLL_INTERVAL", "60"))
    
    poller = GitPoller(backend_url)
    poller.run(poll_interval)

