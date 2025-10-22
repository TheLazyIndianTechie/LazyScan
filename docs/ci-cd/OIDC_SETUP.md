# OIDC Trusted Publishing Setup Guide

This document provides step-by-step instructions for setting up OIDC (OpenID Connect) trusted publishing for automated PyPI releases from GitHub Actions.

## Overview

OIDC trusted publishing allows GitHub Actions to publish packages to PyPI without storing long-lived API tokens. Instead, PyPI trusts GitHub's OIDC token for specific repositories and workflows.

## Benefits

- **Security**: No long-lived secrets stored in GitHub
- **Automated rotation**: OIDC tokens are short-lived and automatically managed
- **Audit trail**: Clear connection between GitHub workflow runs and PyPI publishes
- **Reduced maintenance**: No manual token rotation required

## Prerequisites

1. PyPI account with maintainer permissions for the package
2. TestPyPI account (for testing releases)
3. Repository with GitHub Actions enabled
4. Package already registered on PyPI and TestPyPI

## PyPI Configuration

### 1. Configure Trusted Publisher on PyPI

1. Go to [PyPI Trusted Publishers](https://pypi.org/manage/account/publishing/) (or [TestPyPI](https://test.pypi.org/manage/account/publishing/) for testing)
2. Navigate to your package's settings
3. Click "Add trusted publisher"
4. Fill in the following details:
   - **Owner**: `vinayvidyasagar` (repository owner)
   - **Repository name**: `LazyScan`
   - **Workflow filename**: `release.yml`
   - **Environment**: Leave empty for main branch, or specify environment name

### 2. Configure for TestPyPI

Repeat the same process for TestPyPI to test releases before production:
1. Go to [TestPyPI Trusted Publishers](https://test.pypi.org/manage/account/publishing/)
2. Use the same configuration as above

## GitHub Repository Configuration

### 1. Repository Settings

No additional secrets are needed in the repository since we're using OIDC. The workflows will automatically receive OIDC tokens from GitHub.

### 2. Environment Protection (Optional but Recommended)

For additional security, create GitHub environments:

1. Go to Settings → Environments
2. Create environment named `pypi-production`
3. Add protection rules:
   - Required reviewers
   - Restrict to specific branches (e.g., `main`)
   - Wait timer (e.g., 5 minutes)

### 3. Branch Protection Rules

Ensure branch protection is enabled on `main`:
1. Go to Settings → Branches
2. Add rule for `main` branch:
   - Require status checks to pass
   - Require up-to-date branches
   - Include administrators

## Workflow Configuration

The release workflow (`.github/workflows/release.yml`) uses the following permissions:

```yaml
permissions:
  contents: read
  id-token: write  # Required for OIDC token
```

### OIDC Token Claims

The workflow automatically includes these claims in the OIDC token:
- `repository`: Repository name
- `ref`: Git reference (branch/tag)
- `sha`: Commit SHA
- `workflow`: Workflow name
- `actor`: User who triggered the workflow

## Testing the Setup

### 1. Test with TestPyPI

1. Create a pre-release tag: `git tag v1.0.0-rc1`
2. Push the tag: `git push origin v1.0.0-rc1`
3. Check the workflow runs and publishes to TestPyPI
4. Verify the package appears on TestPyPI

### 2. Test Installation from TestPyPI

```bash
pip install --index-url https://test.pypi.org/simple/ lazyscan==1.0.0-rc1
```

## Production Release Process

### 1. Create Release Tag

```bash
# Create and push version tag
git tag v1.0.0
git push origin v1.0.0
```

### 2. Monitor Release Workflow

1. Check GitHub Actions for workflow status
2. Verify build and test steps pass
3. Confirm PyPI publication succeeds

### 3. Verify Release

1. Check package appears on [PyPI](https://pypi.org/project/lazyscan/)
2. Test installation: `pip install lazyscan==1.0.0`
3. Verify functionality: `lazyscan --version`

## Troubleshooting

### OIDC Token Issues

**Error**: "OIDC token verification failed"
- **Cause**: Mismatch between trusted publisher config and workflow
- **Solution**: Verify repository name, workflow filename, and environment match exactly

### Permission Denied

**Error**: "403 Forbidden" when publishing
- **Cause**: OIDC trust not properly configured
- **Solution**: Check trusted publisher settings on PyPI match workflow configuration

### Workflow Not Triggered

**Error**: Release workflow doesn't run on tag push
- **Cause**: Workflow file issues or branch restrictions
- **Solution**: Check workflow syntax and ensure tags trigger is configured

## Security Best Practices

1. **Use environments**: Protect production releases with GitHub environments
2. **Limit permissions**: Use minimal required permissions in workflows
3. **Monitor releases**: Set up notifications for successful/failed publications
4. **Regular audits**: Review trusted publishers periodically
5. **Test first**: Always test with TestPyPI before production

## Rollback Plan

If OIDC publishing fails:

1. **Disable workflow**: Comment out or disable the release workflow
2. **Manual publish**: Use `twine` with API token as fallback:
   ```bash
   pip install twine
   python -m build
   twine upload dist/* --repository pypi
   ```
3. **Fix configuration**: Address OIDC setup issues
4. **Re-enable**: Restore automated publishing once fixed

## References

- [PyPI Trusted Publishing Documentation](https://docs.pypi.org/trusted-publishers/)
- [GitHub OIDC Documentation](https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/about-security-hardening-with-openid-connect)
- [PyPI OIDC Guide](https://blog.pypi.org/posts/2023-04-20-introducing-trusted-publishers/)
