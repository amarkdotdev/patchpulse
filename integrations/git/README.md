# Git Integrations

GitHub and GitLab integrations for fetching PR/MR diffs and creating change events.

## How to Run

### GitHub Integration

```bash
export GITHUB_TOKEN="your_token"
export GITHUB_REPOS="owner/repo1,owner/repo2"
export BACKEND_URL="http://localhost:8000"

python poller.py
```

### GitLab Integration

```bash
export GITLAB_TOKEN="your_token"
export GITLAB_URL="https://gitlab.com/api/v4"  # or your GitLab instance
export GITLAB_PROJECTS="12345,67890"  # Project IDs
export BACKEND_URL="http://localhost:8000"

python poller.py
```

## Environment Variables

- `GITHUB_TOKEN`: GitHub personal access token
- `GITHUB_REPOS`: Comma-separated list of `owner/repo` pairs
- `GITLAB_TOKEN`: GitLab personal access token
- `GITLAB_URL`: GitLab API URL (default: `https://gitlab.com/api/v4`)
- `GITLAB_PROJECTS`: Comma-separated list of project IDs
- `BACKEND_URL`: Backend API URL
- `POLL_INTERVAL`: Polling interval in seconds (default: 60)

## Features

- Polls open PRs/MRs every 60 seconds
- Fetches full diff content
- Parses diffs into hunks
- Creates ChangeEvent objects and sends to backend
- Tracks processed PRs to avoid duplicates

