<h1 align="center">█▓▒░ 𝙻𝙰𝚉𝚈𝚂𝙲𝙰𝙽 ░▒▓█</h1>
<p align="center">
<strong><em>[𝚂𝚈𝚂𝚃𝙴𝙼::𝚁𝙴𝙰𝙳𝙾𝚄𝚃]</em> 𝚅𝙴𝚁𝚂𝙸𝙾𝙽 `v0.5.0` | 𝚂𝚃𝙰𝚃𝚄𝚂: `OPERATIONAL`</strong>
</p>

<p align="center">
  <img src="https://via.placeholder.com/150" alt="LazyScan Logo" />
</p>

<p align="center">
🌐 **Created by [TheLazyIndianTechie](https://github.com/TheLazyIndianTechie)**
  **For the lazy developer who still wants to look cool while being lazy.**


<div align="center">

## ⚠️ CRITICAL WARNING - USE AT YOUR OWN RISK ⚠️

### 🚨 THIS TOOL PERMANENTLY DELETES FILES 🚨

**BY USING THIS SOFTWARE, YOU ACKNOWLEDGE THAT:**
- This tool will **PERMANENTLY DELETE** files from your system
- You accept **FULL RESPONSIBILITY** for any data loss
- You **WILL NOT SUE** or hold liable the authors for ANY damages
- You have **READ AND AGREED** to the [FULL DISCLAIMER](DISCLAIMER.md)

**[CLICK HERE TO READ THE FULL LEGAL DISCLAIMER](DISCLAIMER.md)**

</div>

---

## ☕ NEW IN v0.4.2

- **First-Run Disclaimer**: Disclaimer now shows only on first use with config management
- **Config Persistence**: User acknowledgment saved in ~/.config/lazyscan/preferences.ini
- **Better UX**: Less intrusive for regular users while maintaining safety awareness

### v0.4.1 Features
- **Version Update**: Resolved PyPI conflict. No new changes from v0.4.0

### v0.4.0 Features

- **Disclaimer Display**: Automatic usage warnings shown on every run
- **Enhanced Safety**: Clear indication of file deletion risks
- **Legal Protection**: Comprehensive legal disclaimer added
- **Skip Option**: Use `--no-logo` to bypass disclaimer display
- **Unreal Engine Support**: Use `--unreal` to scan Unreal projects and clean cache directories like `Intermediate`, `Saved/Logs`, `Saved/Crashes`, `DerivedDataCache`, `Binaries`.

### Troubleshooting Unreal Projects
- **Missing Projects**: Ensure `.uproject` files are present in project directories
- **Permission Errors**: If cache cleaning fails:
  - Run lazyscan with elevated permissions: `sudo lazyscan --unreal`
  - Or manually change directory permissions: `chmod -R 755 /path/to/project/Intermediate`
- **Large Binaries**: The `Binaries` folder can be very large but is needed for editor functionality
- **Project Not Found**: Add custom search paths in the Unreal launcher helper

### Previous (v0.3.0)
- Unity Hub integration for discovering Unity projects
- Cache size calculation for Unity projects (Library, Temp, obj, Logs)
- Interactive project selection with multiple options

## ▓▒░ NEURAL INTERFACE ░▒▓

Welcome to `LAZYSCAN`, the **𝙰𝙳𝚅𝙰𝙽𝙲𝙴𝙳 𝙽𝙴𝚄𝚁𝙰𝙻 𝙳𝙸𝚁𝙴𝙲𝚃𝙾𝚁𝚈 𝚂𝙲𝙰𝙽𝙽𝙸𝙽𝙶 𝚂𝚈𝚂𝚃𝙴𝙼** that infiltrates your file structure with minimal effort. Unleash cybernetic analysis with a retro vibe!

## ▓▒░ CORE SYSTEM ABILITIES ░▒▓

- **🧠 NEURAL SCAN ENGINE** - Multithreaded, efficient file analysis
- **🎮 Unreal Engine Compatible** - Fully integrated support for discovering and managing Unreal Engine projects
- **🕹️ KNIGHT RIDER ANIMATION** - Enjoy retrofuturistic scan progress
- **🌈 CYBERPUNK COLOR OUTPUT** - Neon terminal palette for data visualization
- **⚡ INSTANT DATA ACQUISITION** - Locate digital hoarders effortlessly
- **💤 LAZY-OPTIMIZED ALGORITHMS** - Maximum efficiency, minimal effort
- **💬 INTERACTIVE MODE** - Path selection for the truly lazy
- **🔍 HUMAN-READABLE OUTPUT** - Translates raw sizes into understandable units

## ▓▒░ SYSTEM INSTALLATION ░▒▓

```bash
# From PyPI
pip install lazyscan

# Using pipx for isolated environments
pipx install lazyscan

# Using Homebrew (macOS)
brew tap thelazyindiantechie/tap
brew install lazyscan
```

**[!] COMPATIBILITY NOTE**: Best with ANSI-compatible terminals (iTerm2, Konsole, Windows Terminal).

## ▓▒░ OPERATIONAL COMMANDS ░▒▓

```text
$ lazyscan [-n TOP] [-w WIDTH] [-i] [--no-logo] [path]
```

### 💻 COMMAND EXAMPLES

- **Maximum laziness**: `$ lazyscan --interactive`
- **Targeted analysis**: `$ lazyscan -n 15 -w 60 ~/Downloads`
- **Stealth mode**: `$ lazyscan`
- **Unreal Engine Cleanup**: `$ lazyscan --unreal`
- **Skip disclaimer**: `$ lazyscan --no-logo` (also hides the disclaimer)

## ▓▒░ CYBER VISUALS ░▒▓

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ TARGET ACQUIRED: TOP SPACE HOGS IDENTIFIED ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

## ▓▒░ DISCLAIMER NOTICE ░▒▓

**Important**: LazyScan displays a disclaimer on **first run only** to inform users about:
- Cache deletion may affect application performance
- Applications may need to rebuild caches after deletion
- Always verify files before deletion
- Use at your own risk

The disclaimer requires acknowledgment on first use. After acknowledgment, it won't be shown again unless you reset the configuration (~/.config/lazyscan/preferences.ini). Using the `--no-logo` flag skips both the logo and disclaimer display.

## Unity Hub Integration

LazyScan now includes Unity Hub Integration, allowing you to discover and manage your Unity projects more efficiently. Simply select your projects and execute LazyScan to see detailed insights into your Unity project's cache and other directories.

## Unreal Engine Integration

LazyScan now features Unreal Engine Integration! Automatically discover Unreal projects by:
- Scanning for `.uproject` files in your project directories
- Interactive selection of Unreal projects for cache management
- Cleaning Unreal-specific cache directories:
  - **Intermediate**: Build artifacts and compiled shaders
  - **Saved/Logs**: Editor and runtime logs
  - **Saved/Crashes**: Crash reports and dumps
  - **DerivedDataCache**: Cached asset data
  - **Binaries**: Compiled binaries (optional)

Usage: `lazyscan --unreal` to start the Unreal project scanner.

### 🔧 Troubleshooting Unreal Engine Permissions

If you encounter permission errors when cleaning Unreal Engine caches:

1. **Run with elevated privileges** (recommended for system-wide projects):
   ```bash
   sudo lazyscan --unreal
   ```

2. **Fix permissions for specific directories**:
   ```bash
   # For a single project
   chmod -R 755 /path/to/YourProject/Intermediate
   chmod -R 755 /path/to/YourProject/Saved
   
   # For all cache directories in a project
   find /path/to/YourProject -type d \( -name "Intermediate" -o -name "Saved" -o -name "DerivedDataCache" \) -exec chmod -R 755 {} \;
   ```

3. **Change ownership if needed** (if files are owned by another user):
   ```bash
   sudo chown -R $(whoami) /path/to/YourProject/Intermediate
   ```

4. **Common permission issues**:
   - **"Permission denied"**: The current user doesn't have write access
   - **"Operation not permitted"**: System-protected files (rare in project directories)
   - **"Read-only file system"**: Check if the drive is mounted read-only

5. **Best practices**:
   - Always backup important project files before cleaning
   - Close Unreal Editor before running cache cleanup
   - Verify project functionality after cache cleanup
   - Some caches will be regenerated on next project open

## 📡 SYSTEM STATUS MESSAGES ░▒▓

- `Converting caffeine into code...`
- `Locating your digital hoarding evidence...`

## 🚀 WHY USE NEURAL SCANNING?

In a cluttered digital world, LAZYSCAN gives you the edge with lazy efficiency. Deploy a cutting-edge scan with a single command!

---

**Made with 💜 by TheLazyIndianTechie**
