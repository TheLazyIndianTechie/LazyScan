# LazyScan Improvement Plan
*Comprehensive roadmap to address critical security, maintainability, and reliability issues*

## 🎯 Executive Summary

Based on the comprehensive code analysis using ast-grep, this improvement plan addresses critical issues in LazyScan's codebase, prioritizing security vulnerabilities, the monolithic file structure, and cross-platform compatibility. The plan is structured in phases to ensure systematic improvement while maintaining operational stability.

## 📊 Current State Analysis

### Critical Issues Identified:
- **High-Risk File Operations**: 8 direct file deletion calls without consistent safeguards
- **Monolithic Architecture**: 5,500+ line main file requiring refactoring
- **Input Validation Gaps**: 16 user input points lacking proper validation
- **Platform Limitation**: macOS-only with hardcoded paths
- **Logging Chaos**: 237 print statements instead of structured logging

### Risk Assessment:
- **CRITICAL**: Direct file deletion operations
- **HIGH**: Input validation vulnerabilities
- **HIGH**: Silent security system failures
- **MEDIUM**: Cross-platform compatibility issues

## 🚀 Improvement Plan Overview

### Phase 1: Critical Security Foundation (Priority: CRITICAL)
**Timeline**: 4-6 days  
**Focus**: Eliminate file deletion risks and establish security framework

### Phase 2: Architecture & Reliability (Priority: HIGH)  
**Timeline**: 8-12 days  
**Focus**: Refactor monolithic structure, improve error handling, add comprehensive testing

### Phase 3: Platform & UX Enhancement (Priority: MEDIUM-LOW)
**Timeline**: 4-6 days  
**Focus**: Cross-platform support, CLI improvements, developer tooling

---

## 📋 Detailed Implementation Plan

## Phase 1: Critical Security Foundation

### Step 1: Centralize Safe Deletion + Global Kill Switch ⚠️ CRITICAL
**Goal**: Eliminate critical file deletion risks with fail-closed deletion pathway

**Implementation**:
```bash
# Create new security module
mkdir -p lazyscan/security

# Use ast-grep to find and replace dangerous operations
ast-grep -p 'shutil.rmtree($X, ...)' --rewrite 'SafeDeleter.delete(Path($X), mode="permanent", dry_run=False)' --interactive
ast-grep -p 'os.remove($X)' --rewrite 'SafeDeleter.delete(Path($X), mode="permanent", dry_run=False)' --interactive
```

**Key Features**:
- **SafeDeleter.delete()** with trash-first behavior
- **Global kill switch** via `LAZYSCAN_DISABLE_DELETIONS=1`
- **Path validation** before any deletion
- **Two-step confirmation** for large directories
- **Structured logging** for all decisions

**Deliverables**:
- `lazyscan/security/safe_delete.py`
- Policy-driven deletion with deny-lists
- send2trash integration for cross-platform safety

### Step 2: Harden Path and Input Validation Library ⚠️ CRITICAL
**Goal**: Fix input validation vulnerabilities and ensure consistent path handling

**Implementation**:
```python
# New validators module
lazyscan/security/validators.py

# Key functions:
- canonicalize_path(p) → Path
- is_within_allowed_roots(p, allowed_roots) → bool
- validate_user_supplied_path(p, context) → None | raises PathValidationError
```

**Special Requirements**:
- **Unreal Engine Detection**: Check non-default installations FIRST:
  - `/Volumes/LazyGameDevs/Applications/Unreal/UE_5.5/`
  - `/Volumes/LazyGameDevs/Applications/Unreal/UE_5.6`
- **Cross-platform path handling** with pathlib
- **Symlink and junction defenses**

### Step 3: Security Sentinel and Policy Engine ⚠️ CRITICAL
**Goal**: Mandatory security sentinel that must approve all destructive operations

**Implementation**:
```python
# Security sentinel with fail-closed initialization
lazyscan/security/sentinel.py

# Key features:
- SecuritySentinel.initialize(policy) → SecuritySentinel
- guard_delete(path, context) → None | raises SecurityPolicyError
- Health check at startup (process exits if fails)
```

**Policy Configuration**:
```json
{
  "allowed_roots": {
    "unity": ["~/Library/Application Support/Unity", "~/Projects"],
    "unreal": [
      "/Volumes/LazyGameDevs/Applications/Unreal/UE_5.5/",
      "/Volumes/LazyGameDevs/Applications/Unreal/UE_5.6",
      "~/Documents/Unreal Projects"
    ],
    "chrome": ["~/Library/Caches/Google/Chrome"]
  },
  "behavior": {
    "require_trash_first": true,
    "interactive_double_confirm": true,
    "block_symlinks": true
  }
}
```

---

## Phase 2: Architecture & Reliability

### Step 4: Structured Logging Framework ⚡ HIGH
**Goal**: Replace 237 print statements with structured, configurable logging

**Implementation**:
```bash
# Bulk replacement using ast-grep
ast-grep -p 'print($MSG)' --rewrite 'logger.info($MSG)' --interactive

# Manual tuning for log levels:
# INFO: scan summaries, confirmations
# WARNING: risky inputs, skipped paths  
# ERROR: validation failures, exceptions
# DEBUG: decision traces and sizes
```

**CLI Integration**:
```bash
lazyscan --log-level debug --log-format json unity
```

### Step 5: Error Handling Overhaul ⚡ HIGH
**Goal**: Replace generic exception handling with typed exceptions

**Custom Exception Hierarchy**:
```python
# lazyscan/core/errors.py
PathValidationError
DeletionSafetyError  
SecurityPolicyError
UnsupportedPlatformError
DiscoveryError
ConfigError
UserAbortedError
```

**Implementation**:
- Replace bare `except:` with specific exception handling
- Standardize exit codes at CLI layer
- Add retry logic with backoff for transient operations

### Step 6: Refactor Monolithic File ⚡ HIGH
**Goal**: Split 5,500+ line `lazyscan.py` into cohesive modules

**New Package Structure**:
```
lazyscan/
├── __init__.py (expose __version__)
├── cli/main.py (proper main() function)
├── security/ (safe_delete.py, validators.py, sentinel.py)
├── core/ (scanner.py, reports.py, sizes.py, config.py)
├── apps/ (unity.py, unreal.py, chrome.py)
├── platforms/ (macos.py, windows.py, linux.py)
├── utils/ (logging_config.py, io.py, fmt.py, tty.py)
├── animations/ (progress.py)
└── tests/ (aligned to modules)
```

**Implementation Strategy**:
1. **Phase 1**: Extract security/, utils/, core/errors.py
2. **Phase 2**: Move app-specific logic to apps/ and platform logic to platforms/
3. **Phase 3**: Implement CLI with explicit commands

**Entry Point Fix**:
```python
# setup.py console_scripts
lazyscan=lazyscan.cli.main:main
```

### Step 7: Cross-Platform Support ⚡ HIGH
**Goal**: Implement robust cross-platform support (macOS, Windows, Linux)

**Platform Abstractions**:
```python
# platforms/{macos,windows,linux}.py
def get_known_cache_paths() → List[Path]
def is_system_path(p: Path) → bool
def platform_trash(p: Path) → None
def path_case_sensitivity() → bool
def known_roots() → Dict[str, List[Path]]
```

**Dependencies**:
- `send2trash` for cross-platform deletion
- `platformdirs` for user cache directories
- OS-specific path validation rules

### Step 8: Comprehensive Testing ⚡ HIGH
**Goal**: Add tests for all critical operations, especially deletion and validation

**Test Categories**:
- **Unit Tests**: SafeDeleter, path validators, platform adapters
- **Integration Tests**: Unity/Unreal/Chrome project simulation
- **Property-Based Tests**: Path normalization (using hypothesis)
- **Security Tests**: Policy failures, kill switch behavior

**Coverage Target**: 85%+ on core/security modules

### Step 9: CI/CD Pipeline ⚡ HIGH
**Goal**: Prevent regressions and enforce standards automatically

**GitHub Actions Matrix**:
```yaml
strategy:
  matrix:
    os: [ubuntu-latest, macos-latest, windows-latest]
    python: [3.8, 3.10, 3.12]
```

**Quality Gates**:
- Linting (ruff, black, mypy)
- Coverage reporting (pytest-cov)
- ast-grep checks to prevent print() reintroduction
- No-pager enforcement for git/gh commands

---

## Phase 3: Platform & UX Enhancement

### Step 10: CLI/UX Hardening 🔧 MEDIUM
**Goal**: Reduce user error risk with safer defaults and clearer prompts

**Key Features**:
- **Dry-run by default** for destructive operations
- **Two-step confirmation** for large deletions
- **TTY-aware behavior**: fail-closed in non-interactive environments
- **Type-to-confirm prompts** for critical operations

**New CLI Structure**:
```bash
lazyscan unity --dry-run        # Safe default
lazyscan unreal --yes --permanent  # Explicit flags required
lazyscan chrome --trash         # Trash-first deletion
```

### Step 11: Packaging and Entry Point Fixes 🔧 MEDIUM
**Goal**: Fix console entry mismatch and improve packaging robustness

**Fixes**:
- Implement proper `main()` in `lazyscan/cli/main.py`
- Fix `setup.py` to handle missing `README_PYPI.md`
- Pin minimum Python version (≥3.8 recommended)

### Step 12: Developer Tooling 🔧 MEDIUM
**Goal**: Improve code quality and maintainability

**Tools Configuration**:
```toml
# pyproject.toml
[tool.ruff]
# Forbid bare except, prints, wildcard imports

[tool.black]
line-length = 88

[tool.mypy]
# Gradual typing starting with security modules
```

### Step 13: Documentation 📚 LOW
**Goal**: Document security guarantees and operational procedures

**Deliverables**:
- `SECURITY.md`: Safe deletion model, policy engine, kill switch
- `CONTRIBUTING.md`: Module layout, testing guidance, ast-grep examples
- Updated `WARP.md` with new CLI patterns

### Step 14: Repository Hygiene 🧹 LOW
**Goal**: Comprehensive `.gitignore` for Unity projects and Python artifacts

**Unity .gitignore Patterns** (as per user preference):
```gitignore
# Unity generated
[Ll]ibrary/
[Tt]emp/
[Oo]bj/
[Bb]uild/
[Bb]uilds/
[Ll]ogs/
[Mm]emoryCaptures/
[Uu]serSettings/

# Python
__pycache__/
*.pyc
.pytest_cache/
.coverage
.venv/
dist/
build/
```

---

## 🎯 Implementation Strategy

### Rollout Sequence:
1. **Critical Security Patch** (Steps 1-3): Ship as v0.5.x hotfix
2. **Architecture Refactor** (Steps 4-9): Major version with extensive testing  
3. **Platform & Polish** (Steps 10-14): Minor versions with UX improvements

### Risk Mitigation:
- **Default dry-run** minimizes destructive impact during transition
- **Kill switch** can disable deletions if issues surface  
- **Extensive testing** and CI matrix reduce platform regressions
- **Incremental rollout** with canary releases

### ast-grep Usage Examples:

```bash
# Find dangerous operations
ast-grep --pattern 'shutil.rmtree($_)' --lang python .
ast-grep --pattern 'os.remove($_)' --lang python .

# Replace print statements
ast-grep --pattern 'print($_)' --rewrite 'logger.info($_)' --interactive

# Find input validation points
ast-grep --pattern 'input($_)' --lang python .

# Update imports during refactor
ast-grep --pattern 'from helpers import $_' --rewrite 'from lazyscan.helpers import $_' --interactive
```

---

## 📈 Success Metrics

### Security:
- ✅ Zero direct file deletion calls outside SafeDeleter
- ✅ All user inputs validated before use  
- ✅ Security system cannot fail silently
- ✅ Global kill switch functional

### Code Quality:
- ✅ No files >1000 lines
- ✅ Zero print statements in production code
- ✅ 85%+ test coverage on security modules
- ✅ CI green across all platforms

### Platform Support:
- ✅ Feature parity on macOS, Windows, Linux
- ✅ Unreal Engine detection works with non-default paths
- ✅ Cross-platform cache cleaning functional

---

## 🔗 Dependencies and Prerequisites

### External Dependencies:
```requirements.txt
send2trash>=1.8.0     # Cross-platform trash
platformdirs>=3.0.0   # User directories  
pytest>=7.0.0         # Testing framework
pytest-cov>=4.0.0     # Coverage reporting
hypothesis>=6.0.0     # Property-based testing
```

### Development Tools:
```requirements-dev.txt
ast-grep>=0.5.0       # Pattern matching and refactoring
ruff>=0.0.280         # Fast Python linter
black>=23.0.0         # Code formatting  
mypy>=1.0.0           # Type checking
pre-commit>=3.0.0     # Git hooks
```

---

## 🚧 Timeline and Effort Estimation

| Phase | Steps | Est. Effort | Timeline |
|-------|-------|-------------|----------|
| **Phase 1: Critical Security** | 1-3 | 4-6 days | Week 1-2 |
| **Phase 2: Architecture** | 4-9 | 8-12 days | Week 2-4 |  
| **Phase 3: Enhancement** | 10-14 | 4-6 days | Week 4-5 |
| **Total** | **1-15** | **16-24 days** | **5 weeks** |

### Minimum Viable Security (MVS):
Steps 1-3 can be shipped as an emergency security patch within **1 week** to address critical file deletion risks.

---

*This improvement plan prioritizes security and maintainability while ensuring systematic progress toward a robust, cross-platform disk cleanup tool. Each step includes specific ast-grep patterns for code transformation and clear acceptance criteria for quality assurance.*
