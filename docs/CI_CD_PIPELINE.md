# CI/CD Pipeline Documentation

## Overview

LazyScan implements a comprehensive GitHub Actions CI/CD pipeline that ensures code quality, security, and reliability across multiple platforms and Python versions. The pipeline is designed for automated testing, linting, security scanning, and performance validation.

## Workflow Structure

### Main CI Workflow (`.github/workflows/ci.yml`)

#### Triggers
- **Push**: To `main` and `develop` branches
- **Pull Request**: Targeting `main` and `develop` branches

#### Jobs

##### 1. Test Job (Matrix Strategy)
**Purpose**: Comprehensive testing across platforms and Python versions

**Matrix Configuration**:
- **Operating Systems**: `ubuntu-latest`, `macos-latest`, `windows-latest`
- **Python Versions**: `3.8`, `3.9`, `3.10`, `3.11`, `3.12`
- **Total Combinations**: 15 test environments

**Steps**:
1. **Checkout**: Uses `actions/checkout@v4`
2. **Python Setup**: Uses `actions/setup-python@v4` with matrix version
3. **Dependency Caching**: Platform-aware pip cache using `actions/cache@v4`
   - Cache paths: `~/.cache/pip`, `~/Library/Caches/pip`, `%LOCALAPPDATA%\pip\Cache`
   - Cache key: `${{ runner.os }}-pip-${{ matrix.python-version }}-${{ hashFiles('**/constraints.txt', '**/setup.py') }}`
4. **Dependency Installation**:
   - Upgrade pip, wheel, setuptools
   - Install project with dev dependencies: `pip install -e .[dev] --constraint constraints.txt`
5. **Code Quality Gates**:
   - **Pre-commit hooks**: `pre-commit run --all-files`
   - **Linting**: `ruff check .`
   - **Formatting**: `black --check .`
   - **Type checking**: `mypy lazyscan/ helpers/`
6. **Testing**: `pytest --cov=lazyscan --cov-report=xml --cov-report=term-missing tests/`
7. **Coverage Upload**: Upload `coverage.xml` as artifact
8. **Security Schema Validation**: Custom Python script validating audit encryption schema
9. **CLI Functionality Test**: Basic CLI smoke test
10. **Security Scanning**: `pip-audit` with critical vulnerability detection

##### 2. Codecov Job
**Purpose**: Centralized coverage reporting

**Conditions**: Runs on push or pull request events
**Dependencies**: Requires `test` job completion

**Steps**:
1. Download coverage artifact from Ubuntu/Python 3.11 combination
2. Upload to Codecov using `codecov/codecov-action@v4`
   - Token: `${{ secrets.CODECOV_TOKEN }}`
   - Flags: `unittests`
   - Name: `codecov-umbrella`
   - Fail CI on error: `false`

##### 3. Performance Job
**Purpose**: Performance regression detection

**Conditions**: Only runs on `main` branch pushes
**Dependencies**: Requires `test` job completion

**Steps**:
1. Setup Python 3.11 environment
2. Install dependencies with caching
3. Performance smoke tests:
   - CLI responsiveness (`--version`)
   - Scan performance on test directory
   - Help command performance
4. Time measurements using `time` command

##### 4. Build Job
**Purpose**: Distribution package creation

**Dependencies**: Requires `test` job completion

**Steps**:
1. Setup Python 3.11 environment
2. Install build dependencies
3. Create distribution: `python -m build`
4. Upload build artifacts

### OpenCode Workflow (`.github/workflows/opencode.yml`)

#### Triggers
- **Issue Comments**: When comments contain `/oc` or `/opencode`

#### Purpose
Enables AI-powered code review and assistance via OpenCode integration

**Steps**:
1. Checkout repository
2. Run OpenCode with Claude-3.5-Haiku model
3. Uses `${{ secrets.OPENCODE_API_KEY }}`

## Tooling and Dependencies

### Core Tools
- **Python**: 3.8-3.12 (matrix tested)
- **Testing**: pytest with coverage reporting
- **Linting**: ruff (fast Python linter)
- **Formatting**: black (code formatter)
- **Type Checking**: mypy (static type checker)
- **Pre-commit**: Git hook management
- **Security**: pip-audit (dependency vulnerability scanning)

### Build Tools
- **Build**: Python build system
- **Packaging**: wheel, setuptools

### CI/CD Tools
- **GitHub Actions**: Workflow orchestration
- **Codecov**: Coverage reporting
- **OpenCode**: AI-powered code assistance

## Required Secrets

### Repository Secrets (GitHub Settings → Secrets and variables → Actions)

1. **CODECOV_TOKEN** (Required)
   - Purpose: Upload coverage reports to Codecov
   - Source: Codecov dashboard → Repository Settings → Repository Upload Token
   - Format: UUID string

2. **OPENCODE_API_KEY** (Optional)
   - Purpose: Enable OpenCode AI assistance in PR comments
   - Source: OpenCode platform API key
   - Format: Provider-specific API key format

### Environment Variables (Optional)

The following environment variables can be configured for enhanced functionality:

```bash
# API Keys for Task Master AI integration
ANTHROPIC_API_KEY="sk-ant-api03-..."
PERPLEXITY_API_KEY="pplx-..."
OPENAI_API_KEY="sk-proj-..."
GOOGLE_API_KEY="..."
# ... (see .env.example for complete list)
```

## Platform-Specific Considerations

### Ubuntu (Linux)
- **Primary platform** for coverage reporting
- **Performance testing** environment
- **Build artifact** generation
- Full pip cache support

### macOS
- **Cross-platform compatibility** testing
- Library cache paths: `~/Library/Caches/pip`
- May have different system dependencies

### Windows
- **Cross-platform compatibility** testing
- Library cache paths: `%LOCALAPPDATA%\pip\Cache`
- Path separator differences in scripts
- May require different security permissions

## Caching Strategy

### Pip Dependencies
- **Cache Key**: OS + Python version + dependency hash
- **Cache Paths**: Platform-specific pip cache directories
- **Fallback Keys**: OS + Python version, OS only
- **Files Monitored**: `constraints.txt`, `setup.py`

### Benefits
- Reduces CI execution time by ~60-80%
- Ensures consistent dependency versions across runs
- Platform-aware cache paths

## Validation Results

### Test Coverage
- **Target**: >80% code coverage
- **Reports**: XML format for CI integration
- **Upload**: Automatic to Codecov on PR/push
- **Visualization**: Codecov dashboard integration

### Security Scanning
- **Tool**: pip-audit
- **Scope**: All Python dependencies
- **Severity Filter**: Blocks on CRITICAL vulnerabilities
- **Output**: JSON format with detailed findings

### Performance Benchmarks
- **CLI Responsiveness**: <2 seconds for `--version`
- **Scan Performance**: <5 seconds for small directory scans
- **Help Command**: <1 second response time

## Local Development Validation

### Using `act` (GitHub Actions locally)

```bash
# Install act
brew install act  # macOS
# or download from https://github.com/nektos/act

# Run CI locally (Linux only)
act -j test

# Run with specific platform
act -j test -P ubuntu-latest=catthehacker/ubuntu:act-latest

# Run with secrets
act -j test --secret CODECOV_TOKEN=your_token
```

### Manual Validation Steps

1. **Pre-commit hooks**:
   ```bash
   pre-commit run --all-files
   ```

2. **Code quality checks**:
   ```bash
   ruff check .
   black --check .
   mypy lazyscan/ helpers/
   ```

3. **Testing**:
   ```bash
   pytest --cov=lazyscan --cov-report=term-missing tests/
   ```

4. **Security scan**:
   ```bash
   pip install pip-audit
   pip-audit --format json
   ```

## Troubleshooting

### Common Issues

#### 1. Cache Misses
- **Symptom**: Slow dependency installation
- **Cause**: Cache key mismatch or first run
- **Solution**: Ensure `constraints.txt` is committed and up-to-date

#### 2. Platform-Specific Test Failures
- **Symptom**: Tests pass on Ubuntu but fail on Windows/macOS
- **Cause**: Path separators, permissions, or system dependencies
- **Solution**: Use `os.path` functions and platform detection

#### 3. Codecov Upload Failures
- **Symptom**: Coverage job fails with authentication error
- **Cause**: Missing or invalid `CODECOV_TOKEN`
- **Solution**: Verify token in repository secrets

#### 4. Pre-commit Hook Failures
- **Symptom**: Local commits blocked by pre-commit
- **Cause**: Code doesn't meet quality standards
- **Solution**: Run `pre-commit run --all-files` and fix issues

### Performance Optimization

#### 1. Matrix Optimization
- Use `fail-fast: false` to complete all combinations
- Consider reducing matrix size for faster feedback
- Use `continue-on-error` for non-blocking checks

#### 2. Job Dependencies
- Parallel execution where possible
- Sequential dependencies for artifact sharing
- Conditional execution to reduce resource usage

## Integration with Development Workflow

### Branch Protection
Configure branch protection rules requiring:
- CI checks to pass
- Required reviews for PRs
- Up-to-date branches

### Automated PR Validation
- CI runs automatically on PR creation/update
- Coverage reports linked in PR comments
- Security scan results available in checks

### Release Process
- Build artifacts automatically generated
- Performance benchmarks tracked over releases
- Security scans ensure release readiness

## Future Enhancements

### Planned Improvements
- **Multi-architecture testing** (ARM64, x86_64)
- **Integration testing** with external services
- **Load testing** for performance validation
- **Dependency vulnerability tracking**
- **Automated dependency updates** (Dependabot)

### Monitoring and Analytics
- **CI performance metrics** tracking
- **Failure pattern analysis**
- **Resource usage optimization**
- **Cost monitoring** for GitHub Actions usage

---

*This documentation is automatically updated with CI pipeline changes. Last validated: October 2025*</content>
</xai:function_call">Write file to docs/CI_CD_PIPELINE.md