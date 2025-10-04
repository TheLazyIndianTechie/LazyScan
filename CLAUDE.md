# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

LazyScan is a disk space analysis tool with cyberpunk styling that helps users find and clean large files and caches. The project underwent a major v0.5.0 refactor from a monolithic 5,918-line script into a clean modular architecture with 21 focused modules across 4 main packages.

## Development Commands

### Setup and Installation
```bash
# Development setup
python3 -m venv .venv && source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -e .

# Install development dependencies (or use extras_require)
pip install -e .[dev]
# Alternative manual installation:
# pip install pytest pytest-cov hypothesis ruff black mypy pre-commit
```

### Running the Application
```bash
# Development mode (from source)
python lazyscan.py

# Using console entry point (after editable install)
lazyscan --help
lazyscan --unity
lazyscan --chrome
lazyscan --macos
```

### Testing
```bash
# Run all tests
pytest -q

# Run specific test file
pytest tests/test_unity.py -q

# Run specific test method
pytest tests/test_unity.py::test_prompt_unity_project_selection -q

# Run with coverage
pytest --cov=lazyscan tests/

# Run security tests specifically
python -m pytest tests/security/ -v
```

### Code Quality
```bash
# Format code
black lazyscan/ tests/

# Lint code
ruff check lazyscan/ tests/

# Type checking
mypy lazyscan/
```

### Distribution
```bash
# Build package
pip install build
python -m build

# Note: setup.py reads README_PYPI.md for long_description
```

## Architecture Overview

### Modular Package Structure
The project follows a clean separation of concerns across 4 main packages:

```
lazyscan/
├── cli/          # Command-line interface & argument parsing
├── apps/         # Application-specific integrations (Unity, Unreal, Chrome)
├── core/         # Core functionality (scanner, formatting, config, UI)
├── platforms/    # Platform-specific implementations (macOS, Linux, Windows)
├── security/     # Security framework & safe deletion
└── utils/        # Shared utilities
```

### Entry Points
- **Primary**: `lazyscan/cli/main.py:cli_main()` - Main CLI entry point
- **Backward compatibility**: `lazyscan.py` - Thin wrapper for compatibility
- **Package init**: `lazyscan/__init__.py` - Exports for programmatic use

### Key Modules

#### CLI Module (`lazyscan.cli.main`)
- Handles all argument parsing and validation
- Coordinates between different application modules
- Manages user interaction and confirmation prompts
- Sets up structured logging

#### Apps Module (`lazyscan.apps`)
- **Unity** (`unity.py`): Unity Hub integration, project discovery, cache analysis
- **Unreal** (`unreal.py`): .uproject file discovery, cache directory management
- **Chrome** (`chrome.py`): Profile discovery, cache categorization, safe cleanup

#### Core Module (`lazyscan.core`)
- **Scanner** (`scanner.py`): Directory traversal with progress tracking
- **Formatting** (`formatting.py`): Human-readable output and cyberpunk-styled tables
- **Config** (`config.py`): User preferences and configuration management
- **UI** (`ui.py`): Logo display, disclaimers, Knight Rider animations
- **Logging Config** (`logging_config.py`): Structured logging setup

#### Security Module (`lazyscan.security`)
- **Safe Delete** (`safe_delete.py`): Secure deletion with backup system
- **Validators** (`validators.py`): Path validation and sanitization
- **Sentinel** (`sentinel.py`): Security policy enforcement

#### Platform Modules (`lazyscan.platforms`)
- **macOS** (`macos.py`): macOS-specific cache paths and cleanup
- **Windows** (`windows.py`): Windows cache directories and app paths
- **Linux** (`linux.py`): Linux filesystem conventions

#### Utils Module (`lazyscan.utils`)
- **Logging Config** (`logging_config.py`): Shared logging utilities and configuration

### External Dependencies
The project relies on external `helpers/` modules for:
- **Audit logging** (`helpers.audit`): Operation tracking and logging
- **Security operations** (`helpers.secure_operations`): Secure file operations
- **Recovery system** (`helpers.recovery`): File recovery and restoration

## Testing Architecture

### Test Structure
- Tests use `unittest.TestCase` with `unittest.mock` for mocking
- Tests are organized to mirror the package structure (`tests/core/`, `tests/security/`, `tests/apps/`, etc.)
- Comprehensive mocking prevents destructive actions during testing
- Tests use temporary directories and mock user input

### Test Categories
- **Unit tests**: Individual module functionality
- **Integration tests**: Cross-module interaction
- **Security tests**: Safe deletion and validation logic
- **End-to-end tests**: Complete workflow testing

## Development Guidelines

### Code Conventions
- Follow existing import patterns in each module
- Use the established logging system (`get_logger(__name__)`)
- Maintain cyberpunk styling for UI elements
- Implement proper error handling with audit logging

### Security Requirements
- All file deletion operations MUST use the security framework
- Path validation is required for all user inputs
- Implement confirmation prompts for destructive actions
- Use audit logging for all significant operations

### Platform Support
- Support macOS, Linux, and Windows
- Use platform-specific modules for OS-dependent functionality
- Test cross-platform compatibility for new features

### Adding New Application Support
1. Create new module in `lazyscan/apps/`
2. Implement discovery and cache analysis functions
3. Add command-line arguments in `cli/main.py`
4. Include platform-specific paths in relevant platform modules
5. Add comprehensive tests with mocking

## Important Notes

### Backward Compatibility
- The original `lazyscan.py` is a 16-line compatibility wrapper
- Console script entry point is `lazyscan=lazyscan.cli.main:cli_main`
- All original functionality is preserved through the new modular structure

### Security Considerations
- This tool can permanently delete files - security is paramount
- Safe deletion framework includes backup system and recovery options
- Path validation prevents dangerous operations on system directories
- Audit logging tracks all operations for accountability

### Development Dependencies
The project uses modern Python tooling:
- **pytest**: Testing framework with fixtures and mocking
- **ruff**: Fast Python linter
- **black**: Code formatter
- **mypy**: Static type checking
- **pre-commit**: Git hooks for code quality

### Future Architecture Plans
- Plugin system for extensible app integrations
- Subcommand structure (`lazyscan scan`, `lazyscan clean`)
- Async support for non-blocking operations
- JSON output mode for machine-readable results

## Task Master AI Instructions
**Import Task Master's development workflow commands and guidelines, treat as if import is in the main CLAUDE.md file.**
@./.taskmaster/CLAUDE.md
