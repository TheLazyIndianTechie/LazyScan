# Changelog

## [0.4.0] - 2025-07-31
### Added
- Disclaimer display feature that shows usage warnings on every run
- Comprehensive legal disclaimer (LEGAL_DISCLAIMER.md)
- Test suite for disclaimer functionality (test_disclaimer.py)

### Enhanced
- Documentation updated to inform users about disclaimer display
- Disclaimer can be skipped using the `--no-logo` flag

### Security
- Added prominent warnings about file deletion risks
- Clear indication of user responsibility for data loss

## [0.3.1] - 2025-07-30
### Fixed
- Added missing `--version` argument to argparse configuration
- Users can now check version using `lazyscan --version`

## [0.3.0] - 2023-11-07
### Added
- Unity Hub integration for discovering Unity projects.
- Cache size calculation for Unity project directories like Library, Temp, obj, and Logs.
- Interactive project selection with multiple options for better project management.

### Enhanced
- Cache management and cleaning processes for increased efficiency.

### Tests
- 25 comprehensive tests were added to ensure robust Unity feature integrations.
