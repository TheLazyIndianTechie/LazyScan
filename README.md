# LazyScan 🚀

**The lazy developer's disk space scanner with cyberpunk style**

[![Version](https://img.shields.io/badge/version-0.6.0--beta-blue.svg)](https://github.com/TheLazyIndianTechie/lazyscan)
[![Python](https://img.shields.io/badge/python-3.6%2B-blue.svg)](https://python.org)
[![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Linux%20%7C%20Windows-lightgrey.svg)](https://github.com/TheLazyIndianTechie/lazyscan)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

> *A cyberpunk-styled disk space analyzer that finds what's eating your storage with minimal effort and maximum style.*

---

## 🎉 What's New in v0.6.0-beta - Enterprise System Cache Management!

**Introducing comprehensive cross-platform system cache management with enterprise-grade safety and retention policies:**

### 🗂️ **System Cache Management**
- **Cross-platform cache cleanup** for macOS, Linux, and Windows
- **Intelligent retention policies** with age-based file management
- **Safety classification system** (Safe, Caution, Dangerous operations)
- **Package manager integration** (Homebrew, npm, pip, APT, YUM, Pacman)
- **Docker container cleanup** with dry-run and safety prompts
- **Admin privilege handling** with automatic detection and user confirmation

### 📦 **Package Structure**
```
lazyscan/
├── 📁 cli/          # Command-line interface & argument parsing
├── 📁 apps/         # Application-specific integrations
│   ├── unity.py     # Unity Hub integration & cache management
│   ├── unreal.py    # Unreal Engine project discovery
│   └── chrome.py    # Chrome profile & cache analysis
├── 📁 core/         # Core functionality
│   ├── scanner.py   # Directory scanning with progress
│   ├── formatting.py# Output formatting & human-readable display
│   ├── config.py    # Configuration management
│   └── ui.py        # User interface components
├── 📁 security/     # Security framework & safe deletion
└── 📁 utils/        # Shared utilities
```

### 🔒 **Security First Architecture**
- **SecuritySentinel**: Policy-driven validation with fail-closed design
- **Safe Deletion**: Trash-first approach with comprehensive safeguards
- **Path Validation**: Input sanitization and critical path protection
- **Audit Logging**: Complete operation tracking for compliance
- **Recovery System**: Undo functionality for accidental deletions

---

## 🚀 Quick Start

### Installation

```bash
# From PyPI
pip install lazyscan

# Development installation
git clone https://github.com/TheLazyIndianTechie/lazyscan
cd lazyscan
pip install -e .

# Using pipx (recommended for CLI tools)
pipx install lazyscan
```

### Basic Usage

```bash
# Scan current directory
lazyscan

# Scan with top 10 files, custom bar width
lazyscan -n 10 -w 50 ~/Downloads

# Interactive directory selection
lazyscan --interactive

# Unity project discovery and cache management
lazyscan --unity

# Unreal Engine project scanning
lazyscan --unreal

# Chrome cache analysis (macOS)
lazyscan --chrome

# macOS system cache cleanup
lazyscan --macos

# System-wide cache management with retention policies
lazyscan cache --dry-run  # Preview what would be cleaned
lazyscan cache --force    # Clean all safe cache targets
lazyscan cache --include-docker  # Include Docker cleanup
```

---

## ✨ Features

### 🎯 **Core Functionality**
- **⚡ Fast directory scanning** with cyberpunk-styled progress display
- **🎨 Beautiful terminal UI** with color-coded output and progress bars
- **📊 Human-readable sizes** (B, KB, MB, GB, TB)
- **🎛️ Customizable output** (number of files, bar width)
- **💻 Cross-platform** support (macOS, Linux, Windows)

### 🎮 **Application Integrations**
- **Unity Hub Integration**: Discover projects, analyze cache sizes (Library, Temp, obj, Logs)
- **Unreal Engine Support**: Find .uproject files, clean Intermediate/Saved/DerivedDataCache
- **Chrome Cache Analysis**: Profile-aware cache discovery and cleanup (macOS)
- **macOS System Cache**: Clean system-wide cache directories safely

### 🗂️ **System Cache Management**
- **Cross-Platform Support**: macOS, Linux, and Windows cache cleanup
- **Retention Policies**: Age-based cleanup with configurable retention periods
- **Safety Classification**: Safe, Caution, and Dangerous operation categories
- **Package Manager Caches**: Homebrew, npm, pip, APT, YUM, Pacman support
- **Docker Integration**: Container cleanup with dry-run and safety prompts
- **Admin Privilege Handling**: Automatic detection and user prompting for privileged operations

### 🛡️ **Security & Safety**
- **Comprehensive audit logging** of all operations
- **Backup system** for deleted files with recovery options
- **Safe deletion patterns** with confirmation prompts
- **Path validation** and sanitization
- **First-run disclaimer** with risk acknowledgment

### 💡 **User Experience**
- **Interactive mode** for path selection
- **Progress animations** with Knight Rider-style effects
- **Structured logging** with multiple verbosity levels
- **Recovery system** for restoring deleted files
- **Configuration persistence** for user preferences

---

## 🎯 Command Reference

### Basic Options
```bash
lazyscan [OPTIONS] [PATH]

Options:
  -n, --top NUMBER      Number of top files to display (default: 20)
  -w, --width NUMBER    Progress bar width (default: 40)
  -i, --interactive     Interactive directory selection
  --no-logo            Skip logo and disclaimer display
  --json               Output results in JSON format (machine-readable)
  --exclude PATTERN    Exclude files matching pattern (can be used multiple times)
  --min-size SIZE      Minimum file size to include (e.g., '1MB', '500KB', '2GB')
  --version            Show version information
```

### Application Discovery
```bash
# Game Engine Integration
--unity              Unity Hub project discovery and cache management
--unreal             Unreal Engine project scanning and cache cleanup
  --pick             Force GUI picker for project selection
  --clean            Delete caches immediately after listing
  --build-dir        Include Build directory in calculations
  --no-unityhub      Suppress Unity Hub discovery

# Browser & Application Caches  
--chrome             Chrome profile and cache analysis
--firefox            Firefox cache analysis
--safari             Safari cache analysis
--vscode             VS Code cache analysis
--slack              Slack cache analysis
--discord            Discord cache analysis
--spotify            Spotify cache analysis
```

### System Maintenance
```bash
# macOS System Cache Cleanup
--macos              Clean macOS system cache directories

# Cross-Platform System Cache Management
lazyscan cache       System-wide cache cleanup with retention policies
  --dry-run         Show what would be cleaned without deleting
  --force           Skip safety confirmations for dangerous operations
  --include-docker  Include Docker container cleanup
  --targets TARGET  Clean specific cache targets (homebrew, npm, pip, apt, yum, etc.)
  --platform PLAT   Target platform (macos, linux, windows, auto)

# Security & Recovery
--recovery           Show recovery menu for deleted files
--audit-logs         Display recent audit logs
--recovery-stats     Show recovery system statistics
```

### Advanced Features

#### JSON Output for Scripting
```bash
# Machine-readable JSON output
lazyscan --json /path/to/scan

# Example output:
{
  "scan_path": "/path/to/scan",
  "total_files": 1250,
  "total_dirs": 89,
  "total_size_bytes": 2147483648,
  "top_files_count": 20,
  "files": [
    {
      "path": "/path/to/large/file.dat",
      "size_bytes": 1073741824,
      "size_human": "1 GB"
    }
  ],
  "errors": []
}
```

#### Advanced Filtering
```bash
# Exclude specific patterns
lazyscan --exclude "*.log" --exclude "*.tmp" /var/log

# Only show files larger than 100MB
lazyscan --min-size 100MB ~/Downloads

# Combine filters for targeted analysis
lazyscan --min-size 50MB --exclude "node_modules" --json ~/projects
```

---

## 🏗️ Architecture Overview

### Modular Design Benefits
- **🔧 Maintainable**: Each module has a single, clear responsibility
- **🧩 Extensible**: Easy to add new application integrations
- **🧪 Testable**: Isolated components enable comprehensive testing
- **🔄 Reusable**: Core modules can be imported and used programmatically
- **📦 Scalable**: Clean separation allows for future enhancements

### Key Components

#### CLI Module (`lazyscan.cli`)
- Argument parsing and validation
- Command dispatch to appropriate modules
- User interaction and confirmation handling
- Structured logging setup

#### Apps Module (`lazyscan.apps`)
- **Unity**: Unity Hub integration, project discovery, cache analysis
- **Unreal**: .uproject file discovery, cache directory management  
- **Chrome**: Profile discovery, cache categorization, safe cleanup

#### Core Module (`lazyscan.core`)
- **Scanner**: Directory traversal with progress tracking
- **Formatting**: Human-readable output and table rendering
- **Config**: User preferences and configuration management
- **UI**: Logo display, disclaimers, and visual components

#### Security Module (`lazyscan.security`)
- Safe deletion with backup creation
- Path validation and sanitization
- Input sanitization and security checks

---

## 🛠️ Development

### Setting up Development Environment

```bash
# Clone and setup
git clone https://github.com/TheLazyIndianTechie/lazyscan
cd lazyscan

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e .

# Run tests (when available)
python -m pytest tests/

# Run from source
python lazyscan.py --version
python -m lazyscan.cli.main --version
```

### Project Structure
```
LazyScan/
├── lazyscan.py              # Backward compatibility wrapper (16 lines)
├── lazyscan/               # Main package
│   ├── __init__.py         # Package initialization and exports
│   ├── cli/                # Command-line interface
│   │   ├── __init__.py     # CLI exports  
│   │   └── main.py         # Main CLI logic (738 lines)
│   ├── apps/               # Application integrations
│   │   ├── __init__.py     # App module exports
│   │   ├── unity.py        # Unity Hub integration (298 lines)
│   │   ├── unreal.py       # Unreal Engine support (238 lines)
│   │   └── chrome.py       # Chrome cache analysis (254 lines)
│   ├── core/               # Core functionality
│   │   ├── __init__.py     # Core exports
│   │   ├── scanner.py      # Directory scanning (373 lines)
│   │   ├── formatting.py   # Output formatting (205 lines) 
│   │   ├── config.py       # Configuration (136 lines)
│   │   ├── ui.py           # User interface (163 lines)
│   │   └── logging_config.py # Logging setup (623 lines)
│   └── security/           # Security framework
├── helpers/                # Shared utilities  
│   ├── audit.py            # Audit logging
│   ├── security.py         # Security operations
│   └── recovery.py         # File recovery system
├── setup.py                # Package configuration
└── README.md               # This file
```

---

## 🚨 Important Safety Information

**⚠️ WARNING: This tool can permanently delete files ⚠️**

### Before Using LazyScan:
- **Read the full disclaimer** on first run
- **Understand the risks** of cache deletion
- **Backup important data** before large cleanup operations
- **Test on non-critical directories** first

### Safety Features:
- ✅ **Backup system** creates copies before deletion
- ✅ **Recovery options** available for deleted files  
- ✅ **Audit logging** tracks all operations
- ✅ **Confirmation prompts** for destructive actions
- ✅ **Path validation** prevents dangerous operations

### Recovery Commands:
```bash
# Show recovery options
lazyscan --recovery

# View audit logs
lazyscan --audit-logs  

# Check recovery statistics
lazyscan --recovery-stats
```

---

## 🎨 Sample Output

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ TARGET ACQUIRED: TOP 5 SPACE HOGS IDENTIFIED ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
┌────────────────────────────────────────────────────────────────────────────────────────────┐
│ # │             SIZE ALLOCATION              │   VOLUME   │         LOCATION PATH          │
├────────────────────────────────────────────────────────────────────────────────────────────┤
│  1 │ ████████████████████████████████████████ │   1.2 GB │ ~/Library/Developer/Xcode/DerivedData │
│  2 │ ██████████████████████████████▓▓▓▓▓▓▓▓▓▓ │ 856.3 MB │ ~/Library/Caches/Google/Chrome │
│  3 │ ████████████████████▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓ │ 534.7 MB │ ~/Downloads/node_modules │
│  4 │ ██████████████▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓ │ 412.1 MB │ ~/Library/Logs/DiagnosticReports │
│  5 │ ████████████▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓ │ 287.9 MB │ ~/.npm/_cacache │
└────────────────────────────────────────────────────────────────────────────────────────────┘

[SYS] Total data volume: 3.1 GB
[SYS] Target directory: /Users/developer
[SYS] Scan complete. Have a nice day.
```

---

## 📋 Roadmap

### 🚀 Planned Enhancements
- [x] **Unit & Integration Testing** - Comprehensive test coverage
- [x] **CI/CD Pipeline** - GitHub Actions for automated testing
- [ ] **Plugin Architecture** - Extensible app integration system
- [ ] **Subcommand Structure** - `lazyscan scan`, `lazyscan clean`, etc.
- [ ] **JSON Output Mode** - Machine-readable output format
- [ ] **Configuration Files** - TOML-based configuration system
- [ ] **Cross-platform Cache Paths** - Windows/Linux cache discovery
- [ ] **Performance Optimizations** - Async scanning, caching
- [ ] **Web Dashboard** - Optional web interface for results

### 🛠️ Technical Improvements
- [ ] **Type Hints** - Complete type annotation coverage
- [ ] **Async Support** - Non-blocking file operations
- [ ] **Plugin System** - Entry points for external extensions
- [ ] **Incremental Scanning** - Delta detection between scans
- [ ] **Advanced Filtering** - Exclude patterns, size thresholds

---

## 🤝 Contributing

We welcome contributions! Here's how to get started:

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature-name`
3. **Make your changes** following our coding standards
4. **Add tests** for new functionality
5. **Submit a pull request**

### Development Guidelines
- Follow PEP 8 style guidelines
- Add docstrings for all public functions
- Include type hints where appropriate  
- Write tests for new features
- Update documentation as needed

---

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

---

## 🙋 Support

- **Issues**: [GitHub Issues](https://github.com/TheLazyIndianTechie/lazyscan/issues)
- **Discussions**: [GitHub Discussions](https://github.com/TheLazyIndianTechie/lazyscan/discussions)
- **Documentation**: [Wiki](https://github.com/TheLazyIndianTechie/lazyscan/wiki)

---

<div align="center">

**Made with 💜 by [TheLazyIndianTechie](https://github.com/TheLazyIndianTechie)**

*For the lazy developer who still wants results*

</div>
