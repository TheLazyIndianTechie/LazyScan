## Chrome Cache Cleaning

The `--chrome` flag provides intelligent Chrome browser cache cleaning with profile awareness and safe/unsafe categorization.

### Features

- **Profile Detection**: Automatically discovers all Chrome profiles
- **Smart Categorization**: Separates safe-to-delete cache from user data
- **Interactive Selection**: Choose specific cache types to clean
- **Safety First**: Preserves bookmarks, passwords, and user settings

### Usage

```bash
# Scan and clean Chrome cache interactively
lazyscan --chrome

# Combine with no-logo for cleaner output
lazyscan --chrome --no-logo
```

### Cache Categories

**Safe to Delete:**
- Cache Files (rendering cache, GPU cache)
- Service Worker (offline web app data)
- Temporary Files (downloads, temp data)
- Developer Cache (File System, IndexedDB)
- Media Cache (optimization guides, media)

**Preserved (User Data):**
- History & Bookmarks
- Extensions & Settings
- Passwords & Form Data
- Session Data

### Implementation Details

The Chrome scanner uses a dedicated helper module (`helpers/chrome_cache_helpers.py`) that:
- Intelligently categorizes Chrome data
- Calculates sizes efficiently
- Supports multiple Chrome profiles
- Provides safe deletion patterns

This follows the same architectural pattern as the Unity cache scanner, making the codebase consistent and maintainable.
