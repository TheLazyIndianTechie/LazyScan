# 🛋️ lazy-space

`lazy-space` is a colorful and interactive disk space analyzer for the lazy developer. It quickly shows you what's eating up your disk space with minimal effort.

Created by [TheLazyIndianTechie](https://github.com/TheLazyIndianTechie)

```
 _               _____                     
| |    __ _ ____/ ___/  ___  ___ ____ ___ 
| |   / _` |_  /\___ \ / _ \/ _ `/ __/ -_)
|___| \__,_|/__/ ___/ \/ .__/\_,_/_/  \__/
                       /_/                 
```

## Why lazy-space?

- Instantly find what's hogging your disk space
- Real-time scanning progress with fancy progress bar
- No need to open GUI tools or complex commands
- Just run and see results - perfect for the lazy developer!

## Installation

```bash
pip install .
```

## Usage

```text
lazy-space [-n TOP] [-w WIDTH] [-i] [path]
```

- `-n, --top`: how many top files to display (default: 20)
- `-w, --width`: bar width in characters (default: 40)
- `-i, --interactive`: prompt to choose directory (for the truly lazy)
- `path`: directory to scan (default: current directory)

If `--interactive` is used, a menu of subdirectories is shown and you can also enter a custom path.

### Examples

```bash
# For the laziest - interactive mode to avoid typing paths
lazy-space --interactive

# When you know where to look but are still lazy
lazy-space -n 10 -w 60 ~/Downloads

# The absolute minimum effort way
lazy-space
```

## Features

- 🔄 Real-time scanning progress indicator
- 📊 Beautiful terminal bar charts
- 🎯 Instantly identifies space hogs
- 🛋️ Requires minimal effort - perfect for lazy developers
- 🚀 Scans even large directories efficiently

