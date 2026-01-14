# Contributing to PatchPulse

Thank you for your interest in contributing to PatchPulse! This document provides guidelines and instructions for contributing.

## 🔓 Open Source Commitment

PatchPulse is **100% open source** under the MIT License. We believe in:
- **Transparency**: All code is open and auditable
- **Freedom**: Use, modify, and distribute as you see fit
- **Community**: Built by and for the Kubernetes community
- **No Vendor Lock-in**: Bring your own LLM, self-host everything

## 🤝 How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported in [Issues](https://github.com/amarkdotdev/patchpulse/issues)
2. If not, create a new issue with:
   - Clear description of the bug
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment details (OS, Docker version, etc.)

### Suggesting Features

1. Check if the feature has already been suggested
2. Create a new issue with:
   - Clear description of the feature
   - Use case and benefits
   - Proposed implementation (if you have ideas)

### Code Contributions

1. **Fork the repository**
2. **Create a feature branch**
   ```bash
   git checkout -b feature/amazing-feature
   ```
3. **Make your changes**
   - Follow the code style (see below)
   - Add tests for new features
   - Update documentation
4. **Commit your changes**
   ```bash
   git commit -m 'Add amazing feature'
   ```
   Use clear, descriptive commit messages
5. **Push to your fork**
   ```bash
   git push origin feature/amazing-feature
   ```
6. **Open a Pull Request**
   - Provide a clear description
   - Reference any related issues
   - Ensure all tests pass

## 📝 Code Style

### Python (Backend)

- Follow PEP 8 style guide
- Use type hints where possible
- Maximum line length: 100 characters
- Use `black` for formatting (if available)
- Add docstrings for functions and classes

### Go (Agent)

- Follow standard Go formatting (`go fmt`)
- Use `gofmt` for formatting
- Follow Go naming conventions
- Add comments for exported functions

### General

- Write clear, self-documenting code
- Add comments for complex logic
- Keep functions focused and small
- Write tests for new features

## 🧪 Testing

- Run existing tests before submitting:
  ```bash
  cd app/backend
  pytest tests/
  ```
- Add tests for new features
- Ensure all tests pass
- Test with different LLM providers if applicable

## 📚 Documentation

- Update README.md if adding new features
- Add inline documentation for complex code
- Update API documentation if adding endpoints
- Keep examples up to date

## 🔒 Security

- Never commit API keys or secrets
- Use environment variables for configuration
- Follow security best practices
- Report security issues privately (see SECURITY.md)

## 🤖 LLM Provider Contributions

If you want to add support for a new LLM provider:

1. Add the provider to `app/backend/ai_analyzer.py`
2. Update the `AI_PROVIDERS` dictionary
3. Implement the provider-specific client initialization
4. Update `_call_ai_api` to handle the new provider
5. Add documentation to README.md
6. Test with the new provider

## 📋 Pull Request Checklist

- [ ] Code follows style guidelines
- [ ] Tests added/updated and passing
- [ ] Documentation updated
- [ ] No API keys or secrets committed
- [ ] Commit messages are clear
- [ ] PR description is comprehensive

## 🎯 Areas for Contribution

- **New Guardrails**: Add more Kubernetes best practice checks
- **LLM Providers**: Add support for more AI providers
- **Integrations**: Add support for more Git/notification platforms
- **Documentation**: Improve docs, add examples, tutorials
- **Testing**: Add more test coverage
- **Performance**: Optimize queries, caching, etc.
- **UI/UX**: Improve dashboard and user experience

## 💬 Communication

- Be respectful and inclusive
- Provide constructive feedback
- Ask questions if unsure
- Help others learn

## 📄 License

By contributing, you agree that your contributions will be licensed under the MIT License.

---**Thank you for contributing to PatchPulse! 🚀**