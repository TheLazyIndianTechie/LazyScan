# LazyScan - A lazy way to find what's eating your disk space

[![PyPI version](https://badge.fury.io/py/lazyscan.svg)](https://badge.fury.io/py/lazyscan)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## ⚠️ CRITICAL WARNING - USE AT YOUR OWN RISK ⚠️

### 🚨 THIS TOOL PERMANENTLY DELETES FILES 🚨

**LEGAL DISCLAIMER:**
- This tool will **PERMANENTLY DELETE** files from your system
- Deletions **CANNOT BE UNDONE**
- You accept **FULL RESPONSIBILITY** for any data loss
- The authors accept **NO LIABILITY** for any damages
- By using this software, you agree to **NOT SUE** or hold liable the authors
- **ALWAYS BACKUP YOUR DATA** before using this tool

**BY INSTALLING AND USING THIS SOFTWARE, YOU AGREE TO THE FULL [LEGAL DISCLAIMER](https://github.com/TheLazyIndianTechie/lazyscan/blob/main/DISCLAIMER.md)**

---

## Overview

LazyScan is a powerful disk space analyzer and cache cleaner for developers who want to reclaim disk space with minimal effort. Created by TheLazyIndianTechie.

## Features

- 🚀 **Fast Scanning** - Multi-threaded file system analysis
- 🎮 **Interactive Mode** - Select directories the lazy way
- 🧹 **macOS Cache Cleaning** - Clean system caches safely
- 🎯 **Unity Project Support** - Detect and clean Unity project caches
- 🌐 **Chrome Cache Cleaning** - Smart Chrome browser cache management
- 🎨 **Beautiful Output** - Cyberpunk-themed terminal interface
- 💾 **Multiple App Support** - Clean caches for Slack, Discord, VS Code, and more

## Installation

```bash
pip install lazyscan
```

## Quick Start

```bash
# Scan current directory
lazyscan

# Scan with interactive directory selection
lazyscan -i

# Clean macOS caches (BE CAREFUL!)
lazyscan --macos

# Clean Chrome browser cache
lazyscan --chrome

# Scan Unity projects via Unity Hub
lazyscan --unity
```

## Supported Cache Types

- **macOS System Caches**
- **Chrome Browser** (with profile support)
- **Unity Projects** (via Unity Hub integration)
- **Developer Tools**: VS Code, Xcode
- **Communication Apps**: Slack, Discord, Zoom, Teams
- **Browsers**: Safari, Firefox, Chrome
- **Package Managers**: Homebrew, npm

## Command Options

```
usage: lazyscan [-h] [-n TOP] [-w WIDTH] [-i] [--no-logo] [--macos] [--chrome]
                [--unity] [--clean] [path]

Arguments:
  path                  Directory to scan (default: current directory)

Options:
  -n, --top            Number of files to display (default: 20)
  -w, --width          Bar width in characters (default: 40)
  -i, --interactive    Interactive directory selection
  --no-logo           Hide the LazyScan logo
  --macos             Clean macOS cache directories
  --chrome            Clean Chrome browser cache
  --unity             Scan Unity projects via Unity Hub
  --clean             Auto-clean without prompting (use with caution!)
```

## Safety Features

- Categorizes data into "safe to delete" and "preserve"
- Interactive confirmation before any deletion
- Preserves user data, bookmarks, passwords
- Clear indication of what will be deleted

## System Requirements

- Python 3.6 or higher
- Works best on ANSI-compatible terminals
- macOS-specific features require macOS
- Unity features require Unity Hub

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License.

## Author

Created with 💜 by [TheLazyIndianTechie](https://github.com/TheLazyIndianTechie)

---

**⚠️ FINAL WARNING**: This tool deletes files permanently. Always backup your data first. Use at your own risk. The authors are not responsible for any data loss.
