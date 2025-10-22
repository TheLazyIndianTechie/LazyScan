# Test Reports Directory

This directory contains generated test reports and coverage data.

## Coverage Reports

- `coverage.xml` - Cobertura XML format for CI/CD integration
- `coverage.json` - JSON format coverage data
- `coverage_html/` - HTML coverage report for local viewing

## Test Reports

- `junit.xml` - JUnit XML format test results
- `pytest-report.html` - HTML test report

## Performance Reports

- `*.prof` - Python profiling data
- `*.stats` - Performance statistics

## Usage

Run tests with coverage:
```bash
pytest --cov=lazyscan --cov-report=xml --cov-report=html
```

View HTML coverage report:
```bash
open reports/coverage_html/index.html
```

## CI/CD Integration

The coverage.xml file is automatically uploaded to Codecov in CI workflows.