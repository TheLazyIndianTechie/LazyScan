# Repository Setup and Branch Protection Guide

## Overview

This document outlines the repository configuration requirements for LazyScan's CI/CD pipeline and development workflow.

## Branch Protection Rules

### Main Branch Protection

The `main` branch should be configured with the following protection rules:

#### Required Status Checks
- ✅ **Lint & Format** - Ruff and Black code quality checks
- ✅ **Test Matrix** - Python 3.9-3.12 on ubuntu/macOS/windows
- ✅ **Coverage** - Minimum 80% code coverage requirement
- ✅ **Security** - Bandit and pip-audit security scans
- ✅ **Build** - Package build and validation

#### Additional Protection Settings
- ✅ **Require branches to be up to date** - Ensure latest changes are included
- ✅ **Require review from CODEOWNERS** - At least 1 review required
- ✅ **Dismiss stale reviews** - When new commits are pushed
- ✅ **Restrict pushes to matching branches** - Only allow PRs, no direct pushes
- ✅ **Allow force pushes** - Disabled for safety
- ✅ **Allow deletions** - Disabled for safety

#### Bypass Settings
- 🔒 **Do not allow bypassing** - Admins must follow the same rules
- ⚙️ **Include administrators** - Apply rules to all users

### Development Branch Protection

For feature branches and development workflows:
- ✅ **No direct commits to main** - All changes via Pull Requests
- ✅ **Linear history** - Prefer squash merging for clean history
- ✅ **Automatic branch deletion** - Remove merged feature branches

## Repository Settings

### General Settings
- **Default branch**: `main`
- **Visibility**: Public (or Private based on preference)
- **Features enabled**:
  - Issues
  - Projects
  - Wiki (optional)
  - Discussions (optional)

### Security Settings
- ✅ **Vulnerability alerts** - Enabled
- ✅ **Automated security updates** - Enabled
- ✅ **Private vulnerability reporting** - Enabled
- ✅ **Dependency graph** - Enabled
- ✅ **Code scanning alerts** - Enabled (via workflows)

### Secrets Management

Required repository secrets for CI/CD:

#### PyPI Deployment
```
PYPI_API_TOKEN          # Production PyPI API token (OIDC preferred)
TEST_PYPI_API_TOKEN     # Test PyPI API token (OIDC preferred)
```

#### Code Coverage
```
CODECOV_TOKEN           # Codecov upload token
```

#### Optional Third-party Integrations
```
SONAR_TOKEN            # SonarCloud integration (optional)
SLACK_WEBHOOK          # Deployment notifications (optional)
```

### Environment Configuration

#### Production Environment
- **Name**: `production`
- **Protection**: Require reviewer approval
- **Secrets**: Production API tokens
- **Deployment branches**: `main` only

#### Staging Environment
- **Name**: `staging`
- **Protection**: Optional reviewer approval
- **Secrets**: Test/staging API tokens
- **Deployment branches**: `main`, `develop`, release branches

## OIDC Trust Configuration

### PyPI Trusted Publishing Setup

For secure publishing without API tokens:

1. **Configure PyPI Project**:
   - Project name: `lazyscan`
   - Publisher: `github`
   - Owner: `TheLazyIndianTechie`
   - Repository: `LazyScan`
   - Workflow: `release.yml`
   - Environment: `production` (optional)

2. **Configure Test PyPI Project**:
   - Same settings as above but on test.pypi.org
   - Environment: `staging`

### GitHub OIDC Provider Configuration

The workflows will use GitHub's OIDC provider with these permissions:
```yaml
permissions:
  id-token: write  # Required for OIDC
  contents: read   # Required for checkout
```

## Team and Collaborator Settings

### Access Levels
- **Admin**: Repository owner, lead developers
- **Write**: Core contributors, maintainers
- **Triage**: Issue managers, community moderators
- **Read**: All other contributors

### CODEOWNERS Configuration

Create `.github/CODEOWNERS` file:
```
# Global owners
* @TheLazyIndianTechie

# Core components
/lazyscan/ @TheLazyIndianTechie
/tests/ @TheLazyIndianTechie

# CI/CD and workflows
/.github/ @TheLazyIndianTechie
/tox.ini @TheLazyIndianTechie
/pytest.ini @TheLazyIndianTechie

# Documentation
/docs/ @TheLazyIndianTechie
/README.md @TheLazyIndianTechie
```

## Notification Settings

### Email Notifications
- ✅ **Workflow failures** - Notify on failed CI runs
- ✅ **Security alerts** - Immediate notification for vulnerabilities
- ✅ **Pull request reviews** - Notify reviewers

### Webhook Integrations
- **Slack/Discord** - Optional team notifications
- **Linear/Jira** - Optional project management integration

## Rollback Procedures

### Emergency Rollback Process
1. **Identify issue** - Monitor CI/CD dashboard and alerts
2. **Create hotfix branch** - `hotfix/issue-description`
3. **Fast-track review** - Expedited review process
4. **Deploy fix** - Automatic deployment via CI/CD
5. **Post-incident review** - Document and improve

### Configuration Rollback
- **Workflow files**: Use git history to revert to known good state
- **Branch protection**: Document current settings before changes
- **Secrets**: Rotate compromised secrets immediately
- **Environments**: Disable problematic environments temporarily

## Monitoring and Alerting

### CI/CD Monitoring
- **Workflow status** - Monitor via GitHub Actions dashboard
- **Performance metrics** - Track build times and resource usage
- **Failure rates** - Alert on increased failure rates
- **Security scans** - Monitor vulnerability detection

### Key Metrics to Track
- ✅ **Build success rate** - Target: >98%
- ✅ **Test coverage** - Target: >80%
- ✅ **Build time** - Target: <10 minutes
- ✅ **Time to deployment** - Target: <30 minutes from merge

## Implementation Steps

### Phase 1: Basic Protection
1. Enable branch protection on `main`
2. Set up basic status checks
3. Configure CODEOWNERS file
4. Test with a sample PR

### Phase 2: CI/CD Integration
1. Create workflow files
2. Configure secrets and environments
3. Set up OIDC trust relationships
4. Test full deployment pipeline

### Phase 3: Advanced Features
1. Enable security scanning
2. Configure notifications
3. Set up monitoring dashboards
4. Document rollback procedures

---

**Last Updated**: 2024-01-22
**Next Review**: When adding new workflows or changing repository structure
**Owner**: DevOps Team / Repository Admin
