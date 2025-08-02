# Changelog

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
