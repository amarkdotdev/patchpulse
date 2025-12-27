# PatchPulse

PatchPulse prevents incidents by analyzing infrastructure/app changes and cluster signals, then enforcing pre-flight guardrails with explainable output.

## Quick Start

### Local Development

```bash
# Start all services
make docker-up

# Run tests
make test

# View logs
docker-compose logs -f
```

### Kubernetes Deployment

```bash
# Install via Helm
make helm-install

# Uninstall
make helm-uninstall
```

## Architecture

See [docs/architecture.md](docs/architecture.md) for detailed architecture.

## Components

- **Backend**: FastAPI control plane with policy engine
- **Agent**: Go-based Kubernetes event collector
- **Git Integrations**: GitHub and GitLab change detection
- **Slack Integration**: Risk notifications and approvals
- **UI**: Minimal web interface for risk reports

## Demo

See [docs/demo.md](docs/demo.md) for the complete demo scenario.

## Documentation

- [Architecture](docs/architecture.md)
- [Quickstart](docs/quickstart.md)
- [Demo](docs/demo.md)
- [Threat Model](docs/threat-model.md)
- [Runbooks](docs/runbooks.md)
- [Assumptions](docs/assumptions.md)

## Development

```bash
make lint      # Lint all code
make test      # Run all tests
make build     # Build all containers
make run       # Run backend locally (requires DB)
```

## License

Proprietary - PatchPulse Inc.

