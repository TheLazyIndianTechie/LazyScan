# Contributing to LazyScan

Thank you for your interest in contributing to LazyScan! We welcome contributions from the community to help improve this disk space analysis tool. Whether it's fixing bugs, adding features, improving documentation, or enhancing tests, your help is appreciated.

By participating, you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md) (if we add one) and to follow the guidelines below.

## Getting Started

### Prerequisites
- Python 3.6 or higher
- Git
- A GitHub account

### Development Setup
1. Fork the repository on GitHub.
2. Clone your fork locally:
   ```
   git clone https://github.com/YOUR_USERNAME/lazyscan.git
   cd lazyscan
   ```
3. Create and activate a virtual environment:
   ```
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```
4. Install dependencies in development mode:
   ```
   pip install -e .[dev]
   ```
   This installs runtime deps, plus testing/linting tools (pytest, ruff, black, mypy, pre-commit).

5. Install pre-commit hooks to enforce code quality:
   ```
   pre-commit install
   ```

### Running the Project
- Basic run: `lazyscan` (scans current directory)
- With options: `lazyscan --help`
- Tests: `pytest`
- Lint: `ruff check .`
- Format: `black .`
- Type check: `mypy lazyscan/`

## How to Contribute

### Reporting Bugs
- Check the [Issues](https://github.com/TheLazyIndianTechie/lazyscan/issues) tab for existing reports.
- If your bug isn't listed, open a new issue with:
  - A clear title (e.g., "Scanner crashes on symlinks in Windows").
  - Steps to reproduce.
  - Expected vs. actual behavior.
  - Environment details (OS, Python version, LazyScan version).
  - Screenshots/logs if relevant.

### Suggesting Features
- Use the [Discussions](https://github.com/TheLazyIndianTechie/lazyscan/discussions) or open an issue labeled "enhancement".
- Describe the feature, why it's useful, and any implementation ideas.
- Reference the [ENHANCEMENT_ROADMAP.md](ENHANCEMENT_ROADMAP.md) for planned work.

### Submitting Code Changes
1. Create a feature branch from `main`:
   ```
   git checkout -b feature/your-feature-name
   ```
   - Use descriptive names (e.g., `fix/windows-cache-paths`).

2. Make your changes:
   - Follow coding standards (see below).
   - Add/update tests for new functionality.
   - Update documentation if needed (e.g., README.md, module docstrings).

3. Commit your changes:
   - Use conventional commits: `feat: add Windows support`, `fix: resolve logging duplication`, `docs: update CLI options`.
   - Pre-commit hooks will run automatically.

4. Push and open a Pull Request (PR):
   - Push: `git push origin feature/your-feature-name`
   - Open a PR against `main` on GitHub.
   - In the PR description:
     - Reference related issues (e.g., "Fixes #123").
     - Explain what/why/how.
     - Confirm tests pass and code is formatted.

PRs will be reviewed for:
- Functionality and security (especially deletions).
- Tests and coverage.
- Adherence to standards.
- Documentation updates.

### Coding Standards
- **Style**: Use Black for formatting (`black .`). It enforces PEP 8 with our config.
- **Linting**: Ruff for linting (`ruff check . --fix`). Fixes most issues automatically.
- **Typing**: Use type hints where possible; check with MyPy (`mypy lazyscan/`).
- **Imports**: Consistent with existing modules (e.g., `from ..core.logging_config import get_logger`).
- **Logging**: Use `get_logger(__name__)`; prefer structured logs over prints.
- **Security**: All file ops must use `security/` framework (e.g., `safe_delete`). Add audit logs for changes.
- **Tests**: Write unit/integration tests in `tests/` mirroring structure. Use mocks for file I/O. Aim for 80%+ coverage.
- **Docstrings**: Use Google or NumPy style for public functions/classes.
- **Commit Messages**: Short summary (50 chars), body explaining changes.

### Testing Guidelines
- Run `pytest` before committing.
- Add tests for:
  - Unit: Individual functions (e.g., size formatting).
  - Integration: Module interactions (e.g., CLI dispatch).
  - Security: Edge cases like invalid paths, dry runs.
- Use `unittest.mock` for mocking file system, user input.
- For cross-platform: Test on macOS; use mocks for Windows/Linux paths.

### Documentation
- Update README.md for user-facing changes.
- Add module docstrings.
- Expand [API_DOCUMENTATION.md](API_DOCUMENTATION.md) for new exports.

## Security Issues
If you discover a security vulnerability (e.g., in deletion logic or path handling):
- Do NOT open a public issue.
- Email the maintainer (TheLazyIndianTechie) or use GitHub's private vulnerability reporting.
- We'll triage and respond promptly.

## Questions?
- Join Discussions for general help.
- For code reviews or blockers, @mention in your PR.

Thanks for contributing! Your work helps make LazyScan better for everyone. 🚀