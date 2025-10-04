# Changelog

## [Unreleased] - 2025-01-04
### Documentation
- **Product Requirements Document (PRD)**: Created comprehensive PRD.md covering:
  - Executive summary with product vision and success metrics
  - Detailed feature requirements for all integrations (Unity, Unreal, browsers, dev tools)
  - Technical architecture and performance requirements
  - Product roadmap from v0.6.0 through v1.0.0 (Q1-Q4 2025)
  - Risk analysis and mitigation strategies
  - Success criteria and KPIs for adoption, quality, and safety
  - Open questions and decision points for future development

## [0.6.0-beta] - 2024-10-01
### Added
- Full test suite with 80%+ coverage using pytest and hypothesis
- Security-specific tests for safe deletion and validation
- Platform integration tests for macOS, Linux, and Windows
- Pre-commit hooks with ruff, black, and mypy enforcement
- Subcommand structure: `lazyscan scan`, `lazyscan clean --app unity`
- Basic plugin architecture with entry points for extensibility
- Async scanning support in core/scanner.py for better performance
- JSON output mode with `--json` flag
- Advanced filtering: `--exclude`, `--min-size`
- Expanded app integrations: Firefox, Safari, VSCode basics
- TOML-based user configuration persistence
- CI/CD pipeline stub with GitHub Actions for linting and testing
- Enhanced recovery/audit UI with menu and summaries
- Cross-platform cache paths for Windows and Linux
- Merged logging configurations; removed duplications

### Fixed
- Unused imports and linting issues across modules
- Inline comments and metadata in setup.py
- Logging duplications between core and utils
- Basic diagnostics and type checking passes

### Security
- Verified safe_delete.py with mocks and edge cases
- Added symlinks and critical path blocks
- Full audit logging for all operations

### Other
- Updated classifiers for Python 3.12
- Improved docstrings and API documentation

## [0.5.0] - 2025-08-02
### Added
- **Unreal Engine Support**: New `--unreal` flag for discovering and managing Unreal Engine projects
- Automatic discovery of Unreal projects by scanning for `.uproject` files
- Interactive selection of Unreal projects for cache management
- Cleaning support for Unreal-specific cache directories:
  - Intermediate (build artifacts and compiled shaders)
  - Saved/Logs (editor and runtime logs)
  - Saved/Crashes (crash reports and dumps)
  - DerivedDataCache (cached asset data)
  - Binaries (compiled binaries - optional)
- Helper functions for Unreal project discovery and cache management
- Unreal Launcher integration for project discovery

### Enhanced
- Documentation updated with Unreal Engine usage examples and troubleshooting tips
- Added Unreal Engine to the list of supported features in README

## [0.4.2] - 2025-07-31
### Added
- First-run disclaimer implementation with config management
- Configuration file persistence at ~/.config/lazyscan/preferences.ini
- Disclaimer acknowledgment tracking with timestamp and version

### Changed
- Disclaimer now only shows on first run instead of every run
- Better user experience for regular users

### Technical
- Added configparser dependency for config management
- Added datetime import for timestamp tracking
- New functions: get_config(), save_config(), has_seen_disclaimer(), mark_disclaimer_acknowledged()

## [0.4.1] - 2025-07-31
### Fixed
- Version update to resolve PyPI version conflict
- No functional changes from v0.4.0

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
