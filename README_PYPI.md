# lazyscan 🚀

A lazy way to find what's eating your disk space - now with powerful cache cleaning!

Created by TheLazyIndianTechie - for the lazy developer in all of us.

## Features

- **Fast disk scanning** - Find the biggest files in any directory
- **Visual progress bars** - See file sizes at a glance with cyberpunk-style bars
- **Interactive mode** - Too lazy to type paths? Use `-i` to select directories
- **macOS cache cleaner** - Clean system caches with `--macos`
- **App-specific cleaners** - Clean caches for:
  - Chrome (`--chrome`)
  - Safari (`--safari`)
  - Firefox (`--firefox`)
  - Slack (`--slack`)
  - Discord (`--discord`)
  - Spotify (`--spotify`)
  - VS Code (`--vscode`)
  - Zoom (`--zoom`)
  - Microsoft Teams (`--teams`)
  - Perplexity AI (`--perplexity`)
  - Dia (`--dia`)

## Installation

### From PyPI (Recommended)
```bash
pip install lazyscan
```

### Using pipx (Recommended for isolated installation)
```bash
pipx install lazyscan
```

### From GitHub (Latest development version)
```bash
pip install git+https://github.com/TheLazyIndianTechie/lazyscan.git
```

## Usage

### Basic disk scanning
```bash
# Scan current directory
lazyscan

# Scan specific directory
lazyscan ~/Downloads

# Interactive directory selection
lazyscan -i

# Show top 10 files instead of 20
lazyscan -n 10

# Hide the logo
lazyscan --no-logo
```

### Cache cleaning (macOS only)
```bash
# Clean macOS system caches
lazyscan --macos

# Clean specific app caches
lazyscan --chrome    # Chrome browser
lazyscan --slack     # Slack
lazyscan --discord   # Discord
lazyscan --spotify   # Spotify
lazyscan --vscode    # VS Code
lazyscan --zoom      # Zoom (includes recorded meetings)

# Combine operations
lazyscan --macos ~/Downloads  # Clean cache then scan Downloads
```

## Requirements

- Python 3.6 or higher
- macOS (for cache cleaning features)
- Terminal with color support (recommended)

## Safety

- All cache cleaning operations show what will be deleted before proceeding
- User confirmation is required before any deletion
- Only known cache directories are cleaned
- User data (bookmarks, passwords, etc.) is preserved

## Contributing

Feel free to open issues or submit pull requests on [GitHub](https://github.com/TheLazyIndianTechie/lazyscan)!

## License

MIT License - feel free to use this in your own projects!

---

Made with 💜 by TheLazyIndianTechie
