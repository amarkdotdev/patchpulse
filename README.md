# PatchPulse

**🔓 100% Open Source | 🤖 Bring Your Own LLM | 🚀 Self-Hosted Kubernetes Risk Analysis**

PatchPulse is a self-hosted, open-source solution that prevents production incidents by analyzing infrastructure changes and cluster signals before deployment. It combines rule-based guardrails with AI-powered analysis to provide explainable risk scores and automated enforcement.

## ✨ Key Features

- **🔓 Fully Open Source** - MIT License, no vendor lock-in
- **🤖 Bring Your Own LLM** - Use OpenAI, DeepSeek, Claude, Gemini, or any OpenAI-compatible API
- **🏠 Self-Hosted** - Your data stays on your infrastructure
- **🛡️ 11+ Guardrails** - Rule-based checks for Kubernetes best practices
- **🧠 AI-Powered Analysis** - Security scanning, recommendations, incident prediction
- **⚡ Real-Time** - WebSocket updates and instant notifications
- **🔌 Integrations** - GitHub, GitLab, Slack, Teams, PagerDuty, Email
- **📊 Enterprise Features** - Admission webhooks, policy bundles, SBOM verification, multi-tenancy

## 🚀 Quick Start

### Prerequisites

- Docker Desktop (running)
- Python 3.11+ (for local development)
- Go 1.21+ (for agent development)
- kubectl (for Kubernetes integration)

### 1. Clone the Repository

```bash
git clone https://github.com/amarkdotdev/patchpulse.git
cd patchpulse
```

### 2. Configure Your LLM Provider

PatchPulse supports multiple AI providers. **You only need to provide an API key for ONE provider:**

```bash
# Create .env file
touch .env

# Option 1: OpenAI (recommended for best results)
echo "OPENAI_API_KEY=sk-your-key-here" >> .env

# Option 2: DeepSeek (cost-effective alternative)
# echo "DEEPSEEK_API_KEY=sk-your-key-here" >> .env

# Option 3: Claude (Anthropic)
# echo "ANTHROPIC_API_KEY=sk-ant-your-key-here" >> .env
# Note: Requires: pip install anthropic

# Option 4: Google Gemini
# echo "GEMINI_API_KEY=your-key-here" >> .env
# Note: Requires: pip install google-generativeai

# Optionally specify which provider to use (defaults to first available)
# echo "AI_PROVIDER=openai" >> .env
```

**💡 No LLM? No Problem!** PatchPulse works without AI - you'll get rule-based guardrails and risk scoring. AI features will be disabled gracefully.

### 3. Start PatchPulse

```bash
# Start all services
docker compose up -d

# Check logs
docker compose logs -f backend

# Wait for services to be ready (about 10-15 seconds)
```

### 4. Access the Application

- **Website**: http://localhost:8000/
- **Dashboard**: http://localhost:8000/dashboard
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

### 5. Create Your First Account

1. Go to http://localhost:8000/signup
2. Create an account
3. Start using PatchPulse!

## 📖 Table of Contents

- [Architecture](#-architecture)
- [Configuration](#-configuration)
- [LLM Provider Setup](#-llm-provider-setup)
- [API Usage](#-api-usage)
- [Deployment](#-deployment)
- [Development](#-development)
- [Contributing](#-contributing)
- [License](#-license)

## 🏗️ Architecture

### Components

1. **Backend (FastAPI)**
   - REST API for change events and decisions
   - Policy engine with 11+ guardrails
   - AI-powered risk analysis (bring your own LLM!)
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

4. **Notification Integrations**
   - Slack notifications with interactive approval buttons
   - Email notifications
   - Microsoft Teams integration
   - PagerDuty integration

5. **Dashboard UI**
   - Real-time decision monitoring
   - Risk visualization
   - Analytics and reporting
   - Export functionality

### Data Flow

```
1. Developer creates PR/MR → Git integration detects change
2. Change event sent to backend → Policy engine evaluates
3. AI analysis runs (if configured) → Security scan, recommendations, predictions
4. Risk score calculated (0-100) → Decision made (allow/block)
5. Notification sent to Slack/Teams → Decision stored in database
6. Dashboard updates in real-time via WebSocket
```

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

# AI Provider - Choose ONE (see LLM Provider Setup section)
OPENAI_API_KEY=your_openai_api_key
# OR
# DEEPSEEK_API_KEY=your_deepseek_api_key
# OR
# ANTHROPIC_API_KEY=your_anthropic_api_key
# OR
# GEMINI_API_KEY=your_gemini_api_key

# Optional: Specify which provider to use (defaults to first available)
AI_PROVIDER=openai

# Git Integration
GITHUB_TOKEN=your_github_token
GITHUB_REPOS=owner/repo1,owner/repo2
GITLAB_TOKEN=your_gitlab_token
GITLAB_PROJECTS=12345,67890

# JWT Secret (auto-generated if not set)
JWT_SECRET_KEY=your_jwt_secret
```

### Policy Modes

- **`advisory`**: Logs decisions but doesn't block changes (default)
- **`enforce`**: Blocks high-risk changes (score ≥ 70)

## 🤖 LLM Provider Setup

PatchPulse is **100% open source** and supports **bring your own LLM**. You can use any of these providers:

### Supported Providers

| Provider | Cost | Quality | Setup |
|----------|------|---------|-------|
| **OpenAI** | $$$ | ⭐⭐⭐⭐⭐ | `OPENAI_API_KEY=sk-...` |
| **DeepSeek** | $ | ⭐⭐⭐⭐ | `DEEPSEEK_API_KEY=sk-...` |
| **Claude** | $$$ | ⭐⭐⭐⭐⭐ | `ANTHROPIC_API_KEY=sk-ant-...` |
| **Gemini** | $$ | ⭐⭐⭐⭐ | `GEMINI_API_KEY=...` |

### OpenAI

```bash
export OPENAI_API_KEY=sk-your-key-here
# Or in .env file:
echo "OPENAI_API_KEY=sk-your-key-here" >> .env
```

**Models**: Uses `gpt-4o-mini` by default (cost-effective). You can modify `ai_analyzer.py` to use other models.

### DeepSeek (Recommended for Cost-Conscious Users)

```bash
export DEEPSEEK_API_KEY=sk-your-key-here
# Or in .env file:
echo "DEEPSEEK_API_KEY=sk-your-key-here" >> .env
```

**Models**: Uses `deepseek-chat` by default. OpenAI-compatible API.

### Claude (Anthropic)

```bash
# First install the package
pip install anthropic

export ANTHROPIC_API_KEY=sk-ant-your-key-here
# Or in .env file:
echo "ANTHROPIC_API_KEY=sk-ant-your-key-here" >> .env
```

**Models**: Uses `claude-3-5-sonnet-20241022` by default.

### Google Gemini

```bash
# First install the package
pip install google-generativeai

export GEMINI_API_KEY=your-key-here
# Or in .env file:
echo "GEMINI_API_KEY=your-key-here" >> .env
```

**Models**: Uses `gemini-1.5-pro` by default.

### Using a Custom OpenAI-Compatible API

PatchPulse supports any OpenAI-compatible API endpoint (Ollama, LocalAI, vLLM, etc.):

```bash
# Set a dummy API key (not used for local endpoints)
export OPENAI_API_KEY=not-used

# Set your custom endpoint
export OPENAI_BASE_URL=http://localhost:11434/v1  # Ollama example
# Or
export OPENAI_BASE_URL=http://localhost:8080/v1   # LocalAI example

# Or in .env file:
echo "OPENAI_API_KEY=not-used" >> .env
echo "OPENAI_BASE_URL=http://localhost:11434/v1" >> .env
```

**Examples:**
- **Ollama**: `OPENAI_BASE_URL=http://localhost:11434/v1`
- **LocalAI**: `OPENAI_BASE_URL=http://localhost:8080/v1`
- **vLLM**: `OPENAI_BASE_URL=http://localhost:8000/v1`
- **Any OpenAI-compatible service**: Just set the base URL!

The system will automatically use your custom endpoint with the OpenAI client.

### No LLM Required

**PatchPulse works perfectly without any LLM!** If no API key is provided:
- ✅ All rule-based guardrails work
- ✅ Risk scoring works
- ✅ All integrations work
- ✅ Dashboard works
- ⚠️ AI-powered features are disabled (security scanning, recommendations, predictions)

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
    "diff_hunks": [{
      "file": "k8s/deployment.yaml",
      "hunk": "- limits:\n  cpu: 500m"
    }],
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

## 🚢 Deployment

### Docker Compose (Recommended for Quick Start)

```bash
docker compose up -d
```

### Kubernetes (Helm)

```bash
# Install backend
helm install patchpulse-backend ./helm/backend \
  --namespace patchpulse \
  --create-namespace \
  --set policy.mode=advisory \
  --set ai.openaiApiKey=your_key_here

# Install agent
helm install patchpulse-agent ./helm/agent \
  --namespace patchpulse \
  --set backend.url=http://patchpulse-backend:8000
```

### Production Considerations

- Use environment variables for secrets (never hardcode)
- Set up proper TLS/SSL certificates
- Configure database backups
- Set up monitoring and alerting
- Use a managed PostgreSQL database for production

## 🛠️ Development

### Local Development Setup

```bash
# Backend
cd app/backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload

# Agent
cd app/agent
go run cmd/agent/main.go

# Git Integration
cd app/integrations/git
python poller.py
```

### Running Tests

```bash
# Unit tests
cd app/backend
pytest tests/

# Integration tests
docker compose up -d
./test_api_endpoints.sh
```

### Project Structure

```
patchpulse/
├── app/                    # Application code
│   ├── backend/           # FastAPI backend service
│   │   ├── main.py        # Main application entry point
│   │   ├── models.py      # Pydantic models and SQLAlchemy ORM
│   │   ├── database.py    # Database connection and setup
│   │   ├── policy_engine.py # Policy evaluation and guardrails
│   │   ├── ai_analyzer.py # AI-powered risk analysis (BYO LLM!)
│   │   ├── ai_features.py # Advanced AI features
│   │   ├── auth.py        # Authentication system
│   │   └── requirements.txt
│   ├── agent/             # Kubernetes agent (Go)
│   │   ├── cmd/agent/     # Agent main application
│   │   └── Dockerfile
│   ├── integrations/     # External integrations
│   │   ├── git/           # GitHub/GitLab integration
│   │   └── slack/         # Slack notifications
│   └── ui/                # Dashboard UI
├── docs/                  # Technical documentation
├── helm/                  # Kubernetes Helm charts
├── docker-compose.yml     # Local development setup
└── README.md             # This file
```

## 🛡️ Security

- **API keys never exposed** in logs or responses
- **Least-privilege RBAC** for agent
- **Encrypted database** connections
- **TLS** for all API communications
- **Audit logging** for all decisions
- **Rate limiting** on API endpoints
- **Self-hosted** - your data stays on your infrastructure

See [SECURITY.md](SECURITY.md) for detailed security information.

## 🤝 Contributing

We welcome contributions! PatchPulse is 100% open source and community-driven.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

## 📄 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

**You are free to:**
- ✅ Use PatchPulse commercially
- ✅ Modify the source code
- ✅ Distribute PatchPulse
- ✅ Use it privately
- ✅ Patent use
- ✅ Place warranty

**You must:**
- Include the license and copyright notice

## 🆘 Support

- **Documentation**: http://localhost:8000/docs (when running locally)
- **Issues**: https://github.com/amarkdotdev/patchpulse/issues
- **Discussions**: https://github.com/amarkdotdev/patchpulse/discussions

## 🎯 Roadmap

- [ ] Multi-tenant support (in progress)
- [ ] Custom guardrail DSL
- [ ] Integration with more Git providers
- [ ] Additional AI provider support
- [ ] Compliance reporting
- [ ] Enhanced documentation
- [ ] Local LLM support (Ollama, LocalAI)

## 🙏 Acknowledgments

Built with ❤️ by the open source community. Special thanks to all contributors!

---

**🔓 Open Source | 🤖 Bring Your Own LLM | 🚀 Self-Hosted**

**Made with ❤️ for the Kubernetes community**
