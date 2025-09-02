# LazyScan Agent Configuration

## Build/Test Commands
- **Run all tests**: `python3 -m unittest discover tests/ -v`
- **Run single test**: `python3 -m unittest tests.test_lazyscan.TestLazyScan.test_clean_macos_cache -v`
- **Install package locally**: `python3 setup.py install` or `pip install -e .`
- **Build distribution**: `python3 setup.py sdist bdist_wheel`
- **Run main script**: `python3 lazyscan.py [options]` or `lazyscan [options]`

## Architecture & Structure
- **Main script**: `lazyscan.py` (main CLI application, 1000+ lines)
- **Helpers module**: `helpers/` (security, audit, cache cleaning, Unity/Unreal support)
  - Security framework: `audit.py`, `secure_operations.py`, `confirmation.py`, `recovery.py`
  - Game engine support: `unity_cache_helpers.py`, `unity_hub.py`, `unreal_cache_helpers.py`
  - Application caches: `chrome_cache_helpers.py`
- **Tests**: `tests/` (unittest-based, mocked external dependencies)
- **Package configuration**: `setup.py` (setuptools, console entry point)
- **Version**: Currently v0.5.0, supports Python 3.6+

## Code Style & Conventions
- **Python style**: Standard library preferred, minimal external dependencies
- **Imports**: Grouped by standard/third-party/local, import helpers from `helpers.*`
- **Functions**: Use descriptive names, return human-readable sizes with `human_readable()`
- **Colors**: Terminal colors defined as constants (CYAN, MAGENTA, etc.) with fallbacks
- **Error handling**: Use try/except for file operations, continue on permission errors
- **Security**: All file operations go through security framework with audit logging
- **Testing**: Use unittest.mock for external dependencies, create temp directories in setUp/tearDown
- **CLI**: Uses argparse, supports interactive mode and multiple scanning options
- **File paths**: Use os.path.expanduser() for home directory, glob patterns for cache discovery
