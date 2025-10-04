# LazyScan Monitoring Setup Guide

This guide explains how to set up Sentry error tracking and Socket supply chain security scanning for LazyScan.

## Sentry Error Tracking

### Setup

1. **Create a Sentry Project**
   - Go to [sentry.io](https://sentry.io) and create an account
   - Create a new project for LazyScan (Python platform)
   - Copy the DSN (Data Source Name) from the project settings

2. **Configure Environment Variables**
   ```bash
   export SENTRY_DSN="https://your-dsn@sentry.io/project-id"
   export SENTRY_ENVIRONMENT="development"  # or "production"
   ```

3. **Install Dependencies**
   ```bash
   pip install sentry-sdk>=1.40.0
   ```

### Features Enabled

- **Error Tracking**: Automatically captures and reports all unhandled exceptions
- **Performance Monitoring**: Tracks application performance with 1.0 sample rate
- **Logging Integration**: Captures all log levels and sends them to Sentry
- **Context Information**: Includes platform, Python version, and LazyScan version in all events
- **Release Tracking**: Tracks releases with version information

### Configuration Options

The Sentry integration is configured with:
- **DSN**: Set via `SENTRY_DSN` environment variable
- **Environment**: Set via `SENTRY_ENVIRONMENT` (defaults to "production")
- **Sample Rate**: 1.0 (captures 100% of events)
- **Traces Sample Rate**: 1.0 (captures 100% of performance traces)
- **Release**: Automatically set to `lazyscan@{version}`

### Testing Sentry Integration

To test that Sentry is working:

```python
# This will trigger a test error
import sentry_sdk
sentry_sdk.capture_exception(Exception("Test error from LazyScan"))
```

Or run LazyScan with an invalid command to trigger an error:

```bash
lazyscan invalid-command
```

## Socket Supply Chain Security

### Setup

1. **Create a Socket Account**
   - Go to [socket.dev](https://socket.dev) and create an account
   - Connect your GitHub repository

2. **Get API Token**
   - Go to Settings > API Tokens in Socket dashboard
   - Create a new token for CI/CD use

3. **Configure GitHub Secrets**
   ```bash
   # In your GitHub repository settings
   SOCKET_SECURITY_API_TOKEN=your-api-token-here
   ```

4. **Install Socket CLI (for local testing)**
   ```bash
   npm install -g @socketsecurity/cli
   ```

### CI/CD Integration

Socket scanning is automatically run in GitHub Actions:

- **Pull Request Scans**: Runs on all PRs to check for new security issues
- **Push Scans**: Runs on pushes to main/develop branches
- **Scheduled Scans**: Can be configured for nightly comprehensive scans

### What Socket Detects

Socket scans for various supply chain security issues:

#### Critical Security Issues
- **Malware**: Known malicious packages
- **Typosquatting**: Packages with similar names to legitimate ones
- **Protestware**: Packages that protest or behave unexpectedly
- **Obfuscated Code**: Code that's intentionally hard to read
- **Native Code**: Packages with native binaries
- **Network Access**: Packages that make network requests
- **Shell Access**: Packages that execute shell commands

#### Quality Issues
- **Unpopular Packages**: Packages with very low download counts
- **Minified Code**: Code that's been minified (hard to audit)
- **Deprecated Packages**: Packages that are no longer maintained

#### License Issues
- **Copyleft Licenses**: GPL-style licenses that may affect distribution
- **Unlicensed Code**: Code without clear license terms

### Socket Configuration

The `socket.yml` file configures Socket scanning behavior:

```yaml
# Project information
project:
  name: "lazyscan"
  description: "A lazy way to find what's eating your disk space"
  repository: "https://github.com/TheLazyIndianTechie/lazyscan"

# Alert settings - which issues to flag
alerts:
  enabled: [vulnerability, malware, typo-squat, protestware, ...]
  disabled: [unpopular-package, minified-code, ...]

# Ecosystems to scan
ecosystems: [npm, pypi]

# Scan settings
scan:
  include_dev: true
  follow_dependencies: true
  max_depth: 10
```

### Running Socket Locally

```bash
# Scan the current project
socket scan

# Scan with JSON output
socket scan --json

# Scan specific ecosystems
socket scan --ecosystem pypi
socket scan --ecosystem npm
```

### Interpreting Socket Results

Socket provides a security score and flags issues by severity:

- **Critical**: Immediate action required (malware, severe vulnerabilities)
- **High**: Important issues that should be addressed
- **Medium**: Issues to consider fixing
- **Low**: Minor issues or informational

## Environment Variables Summary

```bash
# Sentry Configuration
SENTRY_DSN=https://your-dsn@sentry.io/project-id
SENTRY_ENVIRONMENT=production

# Socket Configuration (GitHub Secrets)
SOCKET_SECURITY_API_TOKEN=your-socket-api-token
```

## Monitoring Dashboard

### Sentry Dashboard
- View error trends and patterns
- Monitor performance metrics
- Track release health
- Set up alerts for critical issues

### Socket Dashboard
- View security scores over time
- Track dependency vulnerabilities
- Monitor license compliance
- Review supply chain risks

## Troubleshooting

### Sentry Issues

**Sentry not capturing errors:**
- Check that `SENTRY_DSN` is set correctly
- Verify the DSN is for the correct project
- Ensure `sentry-sdk` is installed

**Performance impact:**
- Sentry is configured with 1.0 sample rate for development
- In production, consider reducing sample rates if performance is impacted

### Socket Issues

**Socket scan failing:**
- Check that `SOCKET_SECURITY_API_TOKEN` is set in GitHub secrets
- Verify the token has correct permissions
- Ensure repository is connected to Socket

**False positives:**
- Use `socket.yml` to disable specific alert types
- Report false positives to Socket support
- Consider package allowlists for known safe packages

## Best Practices

### Error Tracking
- Use descriptive error messages
- Include context in error reports
- Set appropriate log levels
- Monitor error rates and trends

### Supply Chain Security
- Regularly review Socket alerts
- Keep dependencies updated
- Audit new dependencies before adding
- Monitor for deprecated packages

### CI/CD Integration
- Don't fail builds on warnings (use `fail_on_issues: false`)
- Set up notifications for critical issues
- Review security reports regularly
- Automate dependency updates where possible

## Support

- **Sentry Documentation**: https://docs.sentry.io
- **Socket Documentation**: https://docs.socket.dev
- **LazyScan Issues**: https://github.com/TheLazyIndianTechie/lazyscan/issues</content>
</xai:function_call">Create a comprehensive monitoring setup guide