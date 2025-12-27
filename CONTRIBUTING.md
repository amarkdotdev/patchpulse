# Contributing to PatchPulse

## Development Setup

1. Clone the repository
2. Copy `.env.example` to `.env` and configure
3. Start services: `make docker-up`
4. Run tests: `make test`

## Code Style

- Python: Follow PEP 8, use black for formatting
- Go: Follow `gofmt` style
- All code must have tests
- Update documentation when adding features

## Adding Guardrails

1. Create guardrail function in `backend/policy_engine.py`
2. Register with `@registry.register` decorator
3. Return `GuardrailResult` with id, severity, message, evidence
4. Add tests in `backend/tests/test_policy_engine.py`

## Submitting Changes

1. Create feature branch
2. Make changes with tests
3. Update documentation
4. Submit pull request

