# LazyScan 🚀

**The lazy developer's disk space scanner with cyberpunk style**

[![CI/CD Status](https://github.com/vinayvidyasagar/LazyScan/actions/workflows/test-matrix.yml/badge.svg)](https://github.com/vinayvidyasagar/LazyScan/actions/workflows/test-matrix.yml)
[![Lint & Format](https://github.com/vinayvidyasagar/LazyScan/actions/workflows/lint-format.yml/badge.svg)](https://github.com/vinayvidyasagar/LazyScan/actions/workflows/lint-format.yml)
[![Security Scan](https://github.com/vinayvidyasagar/LazyScan/actions/workflows/security.yml/badge.svg)](https://github.com/vinayvidyasagar/LazyScan/actions/workflows/security.yml)
[![Coverage](https://codecov.io/gh/vinayvidyasagar/LazyScan/branch/main/graph/badge.svg)](https://codecov.io/gh/vinayvidyasagar/LazyScan)
[![Build](https://github.com/vinayvidyasagar/LazyScan/actions/workflows/build.yml/badge.svg)](https://github.com/vinayvidyasagar/LazyScan/actions/workflows/build.yml)
[![PyPI Version](https://img.shields.io/pypi/v/lazyscan)](https://pypi.org/project/lazyscan/)
[![Python Support](https://img.shields.io/pypi/pyversions/lazyscan)](https://pypi.org/project/lazyscan/)
[![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Linux%20%7C%20Windows-lightgrey.svg)](https://github.com/vinayvidyasagar/LazyScan)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

> *A cyberpunk-styled disk space analyzer that finds what's eating your storage with minimal effort and maximum style.*

---

## 🎉 What's New in v0.5.0 - Major Architecture Refactor!

**We've completely rewritten LazyScan from a monolithic 5,918-line script into a clean, maintainable modular architecture:**

### 🏗️ **New Modular Architecture**
- **21 focused modules** across 4 main packages
- **37% code reduction** with better organization
- **Complete backward compatibility** - your scripts still work!
- **Enhanced maintainability** and extensibility

### 📦 **Package Structure**
```
lazyscan/
├── 📁 cli/          # Command-line interface & argument parsing
├── 📁 apps/         # Application-specific integrations
│   ├── unity.py     # Unity Hub integration & cache management
│   ├── unreal.py    # Unreal Engine project discovery
│   └── chrome.py    # Chrome profile & cache analysis
├── 📁 core/         # Core functionality
│   ├── scanner.py   # Directory scanning with progress
│   ├── formatting.py# Output formatting & human-readable display
│   ├── config.py    # Configuration management
│   └── ui.py        # User interface components
├── 📁 security/     # Security framework & safe deletion
└── 📁 utils/        # Shared utilities
```

---

## 🚀 Quick Start

### Installation

```bash
# From PyPI
pip install lazyscan

# Development installation
git clone https://github.com/TheLazyIndianTechie/lazyscan
cd lazyscan
pip install -e .

# Using pipx (recommended for CLI tools)
pipx install lazyscan
```

### Basic Usage

```bash
# Scan current directory
lazyscan

# Scan with top 10 files, custom bar width
lazyscan -n 10 -w 50 ~/Downloads

# Interactive directory selection
lazyscan --interactive

# Unity project discovery and cache management
lazyscan --unity

# Unreal Engine project scanning
lazyscan --unreal

# Chrome cache analysis (macOS)
lazyscan --chrome

# macOS system cache cleanup
lazyscan --macos
```

---

## ✨ Features

### 🎯 **Core Functionality**
- **⚡ Fast directory scanning** with cyberpunk-styled progress display
- **🎨 Beautiful terminal UI** with color-coded output and progress bars
- **📊 Human-readable sizes** (B, KB, MB, GB, TB)
- **🎛️ Customizable output** (number of files, bar width)
- **💻 Cross-platform** support (macOS, Linux, Windows)

### 🎮 **Application Integrations**
- **Unity Hub Integration**: Discover projects, analyze cache sizes (Library, Temp, obj, Logs)
- **Unreal Engine Support**: Find .uproject files, clean Intermediate/Saved/DerivedDataCache
- **Chrome Cache Analysis**: Profile-aware cache discovery and cleanup (macOS)
- **macOS System Cache**: Clean system-wide cache directories safely

### 🛡️ **Security & Safety**
- **Comprehensive audit logging** of all operations
- **Backup system** for deleted files with recovery options
- **Safe deletion patterns** with confirmation prompts
- **Path validation** and sanitization
- **First-run disclaimer** with risk acknowledgment

### 💡 **User Experience**
- **Interactive mode** for path selection
- **Progress animations** with Knight Rider-style effects
- **Structured logging** with multiple verbosity levels
- **Recovery system** for restoring deleted files
- **Configuration persistence** for user preferences

---

## 🎯 Command Reference

### Basic Options
```bash
lazyscan [OPTIONS] [PATH]

Options:
  -n, --top NUMBER      Number of top files to display (default: 20)
  -w, --width NUMBER    Progress bar width (default: 40)
  -i, --interactive     Interactive directory selection
  --no-logo            Skip logo and disclaimer display
  --version            Show version information
```

### Application Discovery
```bash
# Game Engine Integration
--unity              Unity Hub project discovery and cache management
--unreal             Unreal Engine project scanning and cache cleanup
  --pick             Force GUI picker for project selection
  --clean            Delete caches immediately after listing
  --build-dir        Include Build directory in calculations
  --no-unityhub      Suppress Unity Hub discovery

# Browser & Application Caches
--chrome             Chrome profile and cache analysis
--firefox            Firefox cache analysis
--safari             Safari cache analysis
--vscode             VS Code cache analysis
--slack              Slack cache analysis
--discord            Discord cache analysis
--spotify            Spotify cache analysis
```

### System Maintenance
```bash
# macOS System Cache Cleanup
--macos              Clean macOS system cache directories

# Security & Recovery
--recovery           Show recovery menu for deleted files
--audit-logs         Display recent audit logs
--recovery-stats     Show recovery system statistics
```

---

## 🏗️ Architecture Overview

### Modular Design Benefits
- **🔧 Maintainable**: Each module has a single, clear responsibility
- **🧩 Extensible**: Easy to add new application integrations
- **🧪 Testable**: Isolated components enable comprehensive testing
- **🔄 Reusable**: Core modules can be imported and used programmatically
- **📦 Scalable**: Clean separation allows for future enhancements

### Key Components

#### CLI Module (`lazyscan.cli`)
- Argument parsing and validation
- Command dispatch to appropriate modules
- User interaction and confirmation handling
- Structured logging setup

#### Apps Module (`lazyscan.apps`)
- **Unity**: Unity Hub integration, project discovery, cache analysis
- **Unreal**: .uproject file discovery, cache directory management
- **Chrome**: Profile discovery, cache categorization, safe cleanup

#### Core Module (`lazyscan.core`)
- **Scanner**: Directory traversal with progress tracking
- **Formatting**: Human-readable output and table rendering
- **Config**: User preferences and configuration management
- **UI**: Logo display, disclaimers, and visual components

#### Security Module (`lazyscan.security`)
- Safe deletion with backup creation
- Path validation and sanitization
- Input sanitization and security checks

---

## 🛠️ Development

### Setting up Development Environment

```bash
# Clone and setup
git clone https://github.com/TheLazyIndianTechie/lazyscan
cd lazyscan

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e .

# Run tests (when available)
python -m pytest tests/

# Run from source
python lazyscan.py --version
python -m lazyscan.cli.main --version
```

### Project Structure
```
LazyScan/
├── lazyscan.py              # Backward compatibility wrapper (16 lines)
├── lazyscan/               # Main package
│   ├── __init__.py         # Package initialization and exports
│   ├── cli/                # Command-line interface
│   │   ├── __init__.py     # CLI exports
│   │   └── main.py         # Main CLI logic (738 lines)
│   ├── apps/               # Application integrations
│   │   ├── __init__.py     # App module exports
│   │   ├── unity.py        # Unity Hub integration (298 lines)
│   │   ├── unreal.py       # Unreal Engine support (238 lines)
│   │   └── chrome.py       # Chrome cache analysis (254 lines)
│   ├── core/               # Core functionality
│   │   ├── __init__.py     # Core exports
│   │   ├── scanner.py      # Directory scanning (373 lines)
│   │   ├── formatting.py   # Output formatting (205 lines)
│   │   ├── config.py       # Configuration (136 lines)
│   │   ├── ui.py           # User interface (163 lines)
│   │   └── logging_config.py # Logging setup (623 lines)
│   └── security/           # Security framework
├── helpers/                # Shared utilities
│   ├── audit.py            # Audit logging
│   ├── security.py         # Security operations
│   └── recovery.py         # File recovery system
├── setup.py                # Package configuration
└── README.md               # This file
```

---

## 🔄 CI/CD & Quality Assurance

### Automated Testing & Validation

LazyScan uses a comprehensive CI/CD pipeline to ensure code quality and reliability:

#### 🧪 **Testing Pipeline**
- **Multi-OS Testing**: Ubuntu, macOS, and Windows
- **Python Versions**: 3.9, 3.10, 3.11, 3.12
- **Coverage Reporting**: Minimum 40% coverage with Codecov integration
- **Performance Tests**: Smoke tests and benchmarking

#### 🔍 **Code Quality**
- **Linting**: Ruff for fast Python linting
- **Formatting**: Black for consistent code formatting
- **Type Checking**: MyPy for static type analysis
- **Security Scanning**: Bandit, Safety, and Semgrep for vulnerability detection

#### 🏗️ **Build & Release**
- **Package Building**: Automated wheel and source distribution creation
- **Package Validation**: Twine checks for PyPI readiness
- **Trusted Publishing**: OIDC-based secure deployment to PyPI
- **Release Automation**: Automatic GitHub releases with changelog generation

### 📋 Required Checks for Contributors

All pull requests must pass these automated checks:

✅ **Lint & Format** - Ruff and Black formatting compliance
✅ **Type Check** - MyPy static type validation
✅ **Security Scan** - No high-severity security vulnerabilities
✅ **Test Matrix** - All tests pass on Python 3.9-3.12 across all platforms
✅ **Coverage** - Maintain or improve test coverage
✅ **Build Validation** - Package builds successfully and installs correctly

### 🚀 Release Process

#### Pre-release Testing
```bash
# Create pre-release tag
git tag v1.0.0-rc1
git push origin v1.0.0-rc1

# Automatically publishes to TestPyPI for validation
```

#### Production Release
```bash
# Create release tag
git tag v1.0.0
git push origin v1.0.0

# Automatically publishes to PyPI and creates GitHub release
```

### 🛠️ Local Development Commands

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run linting and formatting
ruff check .
ruff format .
black .

# Run type checking
mypy --ignore-missing-imports lazyscan.py

# Run security checks
bandit -r .
safety check

# Run tests with coverage
pytest --cov=. --cov-report=html

# Build package locally
python -m build
twine check dist/*
```

---

## 🚨 Important Safety Information

**⚠️ WARNING: This tool can permanently delete files ⚠️**

### Before Using LazyScan:
- **Read the full disclaimer** on first run
- **Understand the risks** of cache deletion
- **Backup important data** before large cleanup operations
- **Test on non-critical directories** first

### Safety Features:
- ✅ **Backup system** creates copies before deletion
- ✅ **Recovery options** available for deleted files
- ✅ **Audit logging** tracks all operations
- ✅ **Confirmation prompts** for destructive actions
- ✅ **Path validation** prevents dangerous operations

### Recovery Commands:
```bash
# Show recovery options
lazyscan --recovery

# View audit logs
lazyscan --audit-logs

# Check recovery statistics
lazyscan --recovery-stats
```

---

## 🎨 Sample Output

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ TARGET ACQUIRED: TOP 5 SPACE HOGS IDENTIFIED ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
┌────────────────────────────────────────────────────────────────────────────────────────────┐
│ # │             SIZE ALLOCATION              │   VOLUME   │         LOCATION PATH          │
├────────────────────────────────────────────────────────────────────────────────────────────┤
│  1 │ ████████████████████████████████████████ │   1.2 GB │ ~/Library/Developer/Xcode/DerivedData │
│  2 │ ██████████████████████████████▓▓▓▓▓▓▓▓▓▓ │ 856.3 MB │ ~/Library/Caches/Google/Chrome │
│  3 │ ████████████████████▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓ │ 534.7 MB │ ~/Downloads/node_modules │
│  4 │ ██████████████▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓ │ 412.1 MB │ ~/Library/Logs/DiagnosticReports │
│  5 │ ████████████▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓ │ 287.9 MB │ ~/.npm/_cacache │
└────────────────────────────────────────────────────────────────────────────────────────────┘

[SYS] Total data volume: 3.1 GB
[SYS] Target directory: /Users/developer
[SYS] Scan complete. Have a nice day.
```

---

## 📋 Roadmap

### 🚀 Planned Enhancements
- [x] **CI/CD Pipeline** - GitHub Actions for automated testing, linting, security, and releases
- [x] **Package Build & Release** - Automated PyPI publishing with OIDC trusted publishing
- [ ] **Plugin Architecture** - Extensible app integration system
- [ ] **Subcommand Structure** - `lazyscan scan`, `lazyscan clean`, etc.
- [ ] **JSON Output Mode** - Machine-readable output format
- [ ] **Configuration Files** - TOML-based configuration system
- [ ] **Cross-platform Cache Paths** - Windows/Linux cache discovery
- [ ] **Performance Optimizations** - Async scanning, caching
- [ ] **Web Dashboard** - Optional web interface for results

### 🛠️ Technical Improvements
- [ ] **Type Hints** - Complete type annotation coverage
- [ ] **Async Support** - Non-blocking file operations
- [ ] **Plugin System** - Entry points for external extensions
- [ ] **Incremental Scanning** - Delta detection between scans
- [ ] **Advanced Filtering** - Exclude patterns, size thresholds

---

## 🤝 Contributing

We welcome contributions! Here's how to get started:

### 📋 **Contribution Process**
1. **Fork the repository** and clone it locally
2. **Create a feature branch**: `git checkout -b feature/your-feature-name`
3. **Install development dependencies**: `pip install -r requirements-dev.txt`
4. **Make your changes** following our coding standards
5. **Run the full CI/CD validation locally** (see commands above)
6. **Add tests** for new functionality
7. **Update documentation** as needed
8. **Submit a pull request** with a clear description

### ✅ **Pre-submission Checklist**
Before submitting your PR, ensure all these pass locally:

```bash
# Code quality checks (must pass)
ruff check . && ruff format --check . && black --check .
mypy --ignore-missing-imports lazyscan.py

# Security and safety (must pass)
bandit -r . && safety check

# Tests and coverage (must maintain coverage)
pytest --cov=. --cov-report=term-missing --cov-fail-under=40

# Build validation (must succeed)
python -m build && twine check dist/*
```

### 🎯 **Development Guidelines**
- **Code Style**: Follow Ruff and Black formatting (auto-enforced)
- **Type Safety**: Add type hints for all new functions
- **Testing**: Write tests for new features (pytest framework)
- **Documentation**: Update docstrings and README for user-facing changes
- **Security**: No introduction of security vulnerabilities
- **Compatibility**: Maintain Python 3.9+ compatibility

### 🚫 **Common CI/CD Failures**
- **Formatting Issues**: Run `ruff format . && black .` before committing
- **Type Errors**: Add proper type hints and test with `mypy`
- **Security Vulnerabilities**: Address any findings from `bandit` and `safety`
- **Test Failures**: Ensure all tests pass with `pytest`
- **Coverage Drops**: Maintain test coverage above minimum threshold

### 💡 **Development Tips**
- Use **pre-commit hooks**: `pre-commit install` (automatically formats code)
- Run tests frequently: `pytest -v` for detailed output
- Check coverage locally: `pytest --cov=. --cov-report=html`
- Build and test package: `pip install -e . && lazyscan --version`

---

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

---

## 🙋 Support

- **Issues**: [GitHub Issues](https://github.com/TheLazyIndianTechie/lazyscan/issues)
- **Discussions**: [GitHub Discussions](https://github.com/TheLazyIndianTechie/lazyscan/discussions)
- **Documentation**: [Wiki](https://github.com/TheLazyIndianTechie/lazyscan/wiki)

---

<div align="center">

**Made with 💜 by [TheLazyIndianTechie](https://github.com/TheLazyIndianTechie)**

*For the lazy developer who still wants results*

</div>
