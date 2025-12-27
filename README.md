# PatchPulse

**AI-Powered Pre-Flight Risk Analysis for Kubernetes**

PatchPulse prevents production incidents by analyzing infrastructure changes and cluster signals before deployment. It combines rule-based guardrails with AI-powered analysis to provide explainable risk scores and automated enforcement.

## 🚀 Quick Start

### Prerequisites

- Docker Desktop (running)
- Python 3.11+ (for local development)
- Go 1.21+ (for agent development)
- kubectl (for Kubernetes integration)

### Start with Docker Compose

```bash
# Clone the repository
git clone https://github.com/amarkdotdev/patchpulse.git
cd patchpulse

# Create .env file with your API keys
echo "DEEPSEEK_API_KEY=your_key_here" > .env

# Start all services
docker compose up -d

# Check logs
docker compose logs -f backend

# Access the application
# Website: http://localhost:8000/
# Dashboard: http://localhost:8000/dashboard
# API Docs: http://localhost:8000/docs
```

## 📁 Repository Structure

```
patchpulse/
├── app/                    # Application code
│   ├── backend/           # FastAPI backend service
│   │   ├── main.py        # Main application entry point
│   │   ├── models.py      # Pydantic models and SQLAlchemy ORM
│   │   ├── database.py    # Database connection and setup
│   │   ├── policy_engine.py # Policy evaluation and guardrails
│   │   ├── ai_analyzer.py # AI-powered risk analysis
│   │   ├── ai_features.py # Advanced AI features
│   │   ├── auth.py        # Authentication system
│   │   ├── security.py    # Security utilities
│   │   └── requirements.txt
│   ├── agent/             # Kubernetes agent (Go)
│   │   ├── cmd/agent/     # Agent main application
│   │   └── Dockerfile
│   ├── integrations/     # External integrations
│   │   ├── git/           # GitHub/GitLab integration
│   │   └── slack/         # Slack notifications
│   └── ui/                # Dashboard UI
│       ├── index.html     # Main dashboard
│       └── customer-dashboard.html
├── website/               # Marketing website
│   ├── index.html         # Landing page
│   ├── login.html         # Login page
│   ├── docs/              # Documentation pages
│   └── ...                # Other marketing pages
├── docs/                  # Technical documentation
│   ├── architecture.md    # System architecture
│   ├── quickstart.md      # Quick start guide
│   ├── demo.md            # Demo walkthrough
│   ├── runbooks.md        # Operational runbooks
│   └── threat-model.md    # Security threat model
├── helm/                  # Kubernetes Helm charts
│   ├── backend/           # Backend Helm chart
│   └── agent/             # Agent Helm chart
├── test_for_prod/         # Production test environment
│   ├── setup_cluster.sh   # Setup local k3d cluster
│   ├── deploy_patchpulse.sh # Deploy PatchPulse
│   └── trigger_test_events.sh # Trigger test events
├── docker-compose.yml     # Local development setup
├── Makefile               # Common development tasks
└── README.md              # This file
```

## 🏗️ Architecture

### Components

1. **Backend (FastAPI)**
   - REST API for change events and decisions
   - Policy engine with 11+ guardrails
   - AI-powered risk analysis (DeepSeek API)
   - PostgreSQL database for persistence
   - WebSocket support for real-time updates

2. **Agent (Go)**
   - Kubernetes cluster monitoring
   - Resource snapshotting
   - Event watching
   - Least-privilege RBAC

3. **Git Integrations**
   - GitHub PR analysis
   - GitLab MR analysis
   - Diff parsing and manifest extraction

4. **Slack Integration**
   - Risk notifications
   - Interactive approval buttons
   - Decision summaries

5. **Dashboard UI**
   - Real-time decision monitoring
   - Risk visualization
   - Analytics and reporting
   - Export functionality

### Data Flow

1. Developer creates PR/MR → Git integration detects change
2. Change event sent to backend → Policy engine evaluates
3. AI analysis runs → Security scan, recommendations, predictions
4. Risk score calculated (0-100) → Decision made (allow/block)
5. Notification sent to Slack → Decision stored in database
6. Dashboard updates in real-time via WebSocket

## 🛡️ Features

### AI-Powered Guardrails
- 11+ rule-based guardrails (resource limits, HPA, security contexts, etc.)
- AI security vulnerability scanning
- Explainable decisions with concrete evidence

### Intelligent Risk Analysis
- Hybrid scoring: 60% rule-based + 40% AI
- AI recommendations with code-level suggestions
- Incident prediction based on historical patterns
- Cost optimization suggestions

### Real-Time Monitoring
- Kubernetes agent provides cluster intelligence
- WebSocket updates for instant notifications
- Risk distribution charts and analytics

### Seamless Integrations
- GitHub & GitLab native integration
- Slack notifications with interactive buttons
- REST API for CI/CD pipelines

### Advanced Analytics
- Comprehensive dashboards
- Risk trends and decision history
- Team performance metrics
- Export and reporting

### Enterprise Security
- SOC 2 ready architecture
- Audit logging
- RBAC with least privilege
- Zero API key leakage
- Encrypted communications

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the root directory:

```bash
# Database
DATABASE_URL=postgresql://patchpulse:patchpulse@postgres:5432/patchpulse

# Policy Mode (advisory or enforce)
POLICY_MODE=advisory

# Logging
LOG_LEVEL=INFO

# AI API Key
DEEPSEEK_API_KEY=your_deepseek_api_key

# Git Integration
GITHUB_TOKEN=your_github_token
GITHUB_REPOS=owner/repo1,owner/repo2
GITLAB_TOKEN=your_gitlab_token
GITLAB_PROJECTS=12345,67890

# JWT Secret (auto-generated if not set)
JWT_SECRET_KEY=your_jwt_secret
```

### Policy Modes

- **advisory**: Logs decisions but doesn't block changes
- **enforce**: Blocks high-risk changes (score ≥ 70)

## 📊 API Usage

### Create Change Event

```bash
curl -X POST http://localhost:8000/api/v1/change-events \
  -H "Content-Type: application/json" \
  -d '{
    "source": "github",
    "repo": "org/repo",
    "sha": "abc123",
    "pr_number": 42,
    "branch": "feature-branch",
    "files": ["k8s/deployment.yaml"],
    "diff_hunks": [...],
    "timestamp": "2026-01-01T00:00:00Z"
  }'
```

### Get Decisions

```bash
curl http://localhost:8000/api/v1/decisions?limit=10
```

### Get Analytics

```bash
curl http://localhost:8000/api/v1/analytics/summary
```

See `/docs` for interactive API documentation.

## 🧪 Testing

### Run Unit Tests

```bash
cd app/backend
pytest tests/
```

### Test in Production-Like Environment

```bash
cd test_for_prod
./setup_cluster.sh
./deploy_patchpulse.sh
./trigger_test_events.sh
```

## 🚢 Deployment

### Kubernetes (Helm)

```bash
# Add Helm repository
helm repo add patchpulse https://charts.patchpulse.io
helm repo update

# Install backend
helm install patchpulse-backend patchpulse/backend \
  --namespace patchpulse \
  --set policy.mode=advisory

# Install agent
helm install patchpulse-agent patchpulse/agent \
  --namespace patchpulse \
  --set backend.url=http://patchpulse-backend:8000
```

### Docker Compose (Production)

```bash
docker compose -f docker-compose.prod.yml up -d
```

## 📚 Documentation

- [Architecture](docs/architecture.md) - System design and components
- [Quick Start](docs/quickstart.md) - Get up and running quickly
- [Demo Walkthrough](docs/demo.md) - Step-by-step demo scenario
- [Runbooks](docs/runbooks.md) - Operational guides
- [Threat Model](docs/threat-model.md) - Security analysis

## 🔐 Security

- API keys never exposed in logs or responses
- Least-privilege RBAC for agent
- Encrypted database connections
- TLS for all API communications
- Audit logging for all decisions
- Rate limiting on API endpoints

See [SECURITY.md](SECURITY.md) for detailed security information.

## 🛠️ Development

### Local Development

```bash
# Backend
cd app/backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload

# Agent
cd app/agent
go run cmd/agent/main.go

# Git Integration
cd app/integrations/git
python poller.py
```

### Makefile Commands

```bash
make lint          # Run linters
make test          # Run tests
make docker-up     # Start Docker Compose
make docker-down   # Stop Docker Compose
make build         # Build Docker images
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📄 License

Copyright © 2026 PatchPulse. All rights reserved.

## 🆘 Support

- Documentation: http://localhost:8000/docs
- Issues: https://github.com/amarkdotdev/patchpulse/issues
- Email: support@patchpulse.io

## 🎯 Roadmap

- [ ] Multi-tenant support
- [ ] Custom guardrail DSL
- [ ] Integration with more Git providers
- [ ] Advanced AI models
- [ ] Compliance reporting
- [ ] Mobile app

---

**Built with ❤️ by the PatchPulse team**
