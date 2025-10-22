# Branch Protection Configuration

This document outlines the recommended branch protection rules for the LazyScan repository to ensure code quality and security.

## Overview

Branch protection rules help maintain code quality by requiring certain checks to pass before code can be merged into protected branches.

## Main Branch Protection

Configure the following protection rules for the `main` branch:

### Required Settings

1. **Require status checks to pass before merging**
   - Enable this option
   - Require branches to be up to date before merging
   - Required status checks:
     - `lint-format / lint-and-format`
     - `test-matrix / test (3.9, ubuntu-latest)`
     - `test-matrix / test (3.10, ubuntu-latest)`
     - `test-matrix / test (3.11, ubuntu-latest)`
     - `test-matrix / test (3.12, ubuntu-latest)`
     - `test-matrix / test (3.9, macos-latest)`
     - `test-matrix / test (3.12, macos-latest)`
     - `test-matrix / test (3.9, windows-latest)`
     - `test-matrix / test (3.12, windows-latest)`
     - `coverage / coverage-report`
     - `security / security-scan`
     - `build / build`
     - `build / build-validation (ubuntu-latest, 3.9)`
     - `build / build-validation (macos-latest, 3.9)`
     - `build / build-validation (windows-latest, 3.9)`

2. **Require pull request reviews**
   - Required number of reviewers: 1
   - Dismiss stale reviews when new commits are pushed
   - Require review from code owners (when CODEOWNERS file exists)
   - Allow specified actors to bypass required reviews: Repository administrators only

3. **Require conversation resolution**
   - Enable this to ensure all PR conversations are resolved before merging

4. **Include administrators**
   - Enable this to ensure administrators also follow the protection rules

5. **Allow force pushes**
   - **Disable** this option for security

6. **Allow deletions**
   - **Disable** this option to prevent accidental branch deletion

### Configuration Steps

1. Navigate to repository **Settings** → **Branches**
2. Click **Add rule** or edit existing rule for `main`
3. Configure the settings as outlined above
4. Click **Create** or **Save changes**

## Development Branch Protection (Optional)

For a `develop` branch, configure similar but slightly more relaxed rules:

### Required Settings

1. **Require status checks to pass before merging**
   - Enable this option
   - Require branches to be up to date before merging
   - Required status checks: Same as main branch

2. **Require pull request reviews**
   - Required number of reviewers: 1 (can be lower than main)
   - Dismiss stale reviews when new commits are pushed
   - Do not require review from code owners

3. **Allow force pushes**
   - **Allow** for development branches (optional)

## CODEOWNERS File

Create a `.github/CODEOWNERS` file to define code ownership:

```
# Global ownership
* @vinayvidyasagar

# CI/CD workflows
/.github/workflows/ @vinayvidyasagar

# Security and configuration files
/pyproject.toml @vinayvidyasagar
/requirements*.txt @vinayvidyasagar
/.github/workflows/security.yml @vinayvidyasagar

# Documentation
/docs/ @vinayvidyasagar
/README.md @vinayvidyasagar
/CHANGELOG.md @vinayvidyasagar

# Tests
/tests/ @vinayvidyasagar
/pytest.ini @vinayvidyasagar
/.coveragerc @vinayvidyasagar
```

## Status Check Configuration

The following GitHub Actions workflows provide status checks:

### Core Quality Checks

1. **lint-format** (`.github/workflows/lint-format.yml`)
   - Runs Ruff linting
   - Runs Black formatting
   - Runs Mypy type checking
   - Runs Bandit security scanning

2. **test-matrix** (`.github/workflows/test-matrix.yml`)
   - Tests across Python 3.9-3.12
   - Tests on Ubuntu, macOS, Windows
   - Includes smoke tests and performance tests

3. **coverage** (`.github/workflows/coverage.yml`)
   - Generates coverage report
   - Uploads to Codecov
   - Enforces minimum coverage thresholds

4. **security** (`.github/workflows/security.yml`)
   - Runs security scanning with multiple tools
   - Uploads SARIF results to GitHub Security

### Build and Release Checks

5. **build** (`.github/workflows/build.yml`)
   - Builds source and wheel distributions
   - Validates with twine
   - Tests package installation

6. **release** (`.github/workflows/release.yml`)
   - Triggered only on version tags
   - Publishes to PyPI using OIDC trusted publishing

## Bypass Options

### Emergency Procedures

In emergency situations, repository administrators can:

1. Temporarily disable branch protection
2. Apply hotfix directly to main
3. Re-enable branch protection immediately after
4. Create follow-up PR for review and documentation

### Scheduled Maintenance

For planned maintenance:

1. Create maintenance branch from main
2. Apply changes to maintenance branch
3. Create PR with detailed explanation
4. Use normal review process

## Monitoring and Alerts

### GitHub Settings

1. **Notifications**
   - Enable email notifications for protection rule bypasses
   - Enable notifications for failed status checks

2. **Security Alerts**
   - Enable Dependabot alerts
   - Enable secret scanning alerts
   - Enable code scanning alerts

### Recommended Monitoring

1. Review protection rule bypasses monthly
2. Monitor status check failure rates
3. Review CODEOWNERS assignments quarterly
4. Audit branch protection settings during security reviews

## Troubleshooting

### Status Check Issues

**Problem**: Status check not appearing in required list
- **Solution**: Ensure workflow runs on PR and has correct job names

**Problem**: Status check failing unexpectedly
- **Solution**: Check workflow logs and fix underlying issues

### Review Issues

**Problem**: Cannot merge due to review requirement
- **Solution**: Request review from appropriate team member or code owner

**Problem**: Stale review blocking merge
- **Solution**: Push new commit to dismiss stale reviews, then request new review

## Security Considerations

1. **Minimum Reviews**: Always require at least one review for production code
2. **Status Checks**: Never bypass security or test status checks
3. **Administrator Inclusion**: Include administrators in protection rules
4. **Code Owners**: Use CODEOWNERS for critical files and directories
5. **Audit Trail**: Monitor and log all protection rule bypasses

## References

- [GitHub Branch Protection Documentation](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/defining-the-mergeability-of-pull-requests/about-protected-branches)
- [GitHub CODEOWNERS Documentation](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners)
