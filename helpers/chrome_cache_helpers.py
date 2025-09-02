import os
import glob


def compute_directory_size(path):
    """Recursively calculates the total file size of a directory."""
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if os.path.exists(fp):
                total_size += os.path.getsize(fp)
    return total_size


def get_chrome_cache_targets(profile_path=None):
    """Returns a dictionary of cache target directories for Chrome.

    Args:
        profile_path: Path to a specific Chrome profile. If None, uses the default profile.

    Returns:
        Dictionary mapping cache category names to their paths.
    """
    chrome_base = os.path.expanduser('~/Library/Application Support/Google/Chrome')

    if profile_path is None:
        profile_path = os.path.join(chrome_base, 'Default')

    cache_targets = {
        "Cache": os.path.join(profile_path, 'Cache'),
        "Code Cache": os.path.join(profile_path, 'Code Cache'),
        "GPUCache": os.path.join(profile_path, 'GPUCache'),
        "Service Worker Cache": os.path.join(profile_path, 'Service Worker/CacheStorage'),
        "Service Worker Scripts": os.path.join(profile_path, 'Service Worker/ScriptCache'),
        "Media Cache": os.path.join(profile_path, 'Media Cache'),
        "File System": os.path.join(profile_path, 'File System'),
        "IndexedDB": os.path.join(profile_path, 'IndexedDB'),
        "Local Storage": os.path.join(profile_path, 'Local Storage'),
        "Session Storage": os.path.join(profile_path, 'Session Storage'),
        "Web Storage": os.path.join(profile_path, 'WebStorage'),
    }

    # Add Chrome-wide cache directories
    cache_targets.update({
        "Shader Cache": os.path.join(chrome_base, 'ShaderCache'),
        "GrShader Cache": os.path.join(chrome_base, 'GrShaderCache'),
        "Component CRX Cache": os.path.join(chrome_base, 'component_crx_cache'),
        "Screen AI": os.path.join(chrome_base, 'screen_ai'),
        "Optimization Guide": os.path.join(chrome_base, 'optimization_guide_model_store'),
        "Crash Reports": os.path.join(chrome_base, 'CrashReports'),
        "Crashpad": os.path.join(chrome_base, 'Crashpad/completed'),
    })

    return cache_targets


def get_chrome_profiles():
    """Discovers all Chrome profiles.

    Returns:
        List of tuples containing (profile_name, profile_path).
    """
    chrome_base = os.path.expanduser('~/Library/Application Support/Google/Chrome')
    profiles = []

    if not os.path.exists(chrome_base):
        return profiles

    # Always include Default profile
    default_path = os.path.join(chrome_base, 'Default')
    if os.path.exists(default_path):
        profiles.append(("Default", default_path))

    # Find all Profile directories
    for item in os.listdir(chrome_base):
        if item.startswith('Profile ') and os.path.isdir(os.path.join(chrome_base, item)):
            profiles.append((item, os.path.join(chrome_base, item)))

    return profiles


def categorize_chrome_cache(profile_path=None):
    """Categorizes Chrome cache data into safe and unsafe to delete.

    Args:
        profile_path: Path to a specific Chrome profile. If None, scans all profiles.

    Returns:
        Dictionary with categorized cache data.
    """
    categories = {
        'safe': {
            'Cache Files': [],
            'Service Worker': [],
            'Temporary Files': [],
            'Developer Cache': [],
            'Media Cache': [],
        },
        'unsafe': {
            'User Data': [],
            'Extensions': [],
            'Settings': [],
        }
    }

    chrome_base = os.path.expanduser('~/Library/Application Support/Google/Chrome')

    # Safe patterns - can be deleted without losing user data
    safe_patterns = {
        'Cache Files': ['*/Cache/*', '*/Code Cache/*', '*/GPUCache/*',
                       'ShaderCache/*', 'GrShaderCache/*', 'component_crx_cache/*'],
        'Service Worker': ['*/Service Worker/CacheStorage/*', '*/Service Worker/ScriptCache/*'],
        'Temporary Files': ['*/Temp/*', '*/.com.google.Chrome.*', 'screen_ai/*'],
        'Developer Cache': ['*/File System/*', '*/IndexedDB/*'],
        'Media Cache': ['*/Media Cache/*', 'optimization_guide_model_store/*'],
    }

    # Unsafe patterns - contains user data, bookmarks, passwords, etc.
    unsafe_patterns = {
        'User Data': ['*/History*', '*/Bookmarks*', '*/Favicons*', '*/Login Data*'],
        'Extensions': ['*/Extensions/*', '*/Extension State/*', '*/Local Extension Settings/*'],
        'Settings': ['*/Preferences', '*/Secure Preferences', '*/Local State'],
    }

    # Scan safe patterns
    for category, patterns in safe_patterns.items():
        for pattern in patterns:
            full_pattern = os.path.join(chrome_base, pattern)
            for path in glob.glob(full_pattern):
                try:
                    if os.path.isfile(path):
                        size = os.path.getsize(path)
                        categories['safe'][category].append((path, size, 'file'))
                    elif os.path.isdir(path):
                        size = compute_directory_size(path)
                        if size > 0:
                            categories['safe'][category].append((path, size, 'dir'))
                except (OSError, PermissionError):
                    continue

    # Scan unsafe patterns (for reporting only)
    for category, patterns in unsafe_patterns.items():
        for pattern in patterns:
            full_pattern = os.path.join(chrome_base, pattern)
            for path in glob.glob(full_pattern):
                try:
                    if os.path.isfile(path):
                        size = os.path.getsize(path)
                        categories['unsafe'][category].append((path, size, 'file'))
                    elif os.path.isdir(path):
                        size = compute_directory_size(path)
                        if size > 0:
                            categories['unsafe'][category].append((path, size, 'dir'))
                except (OSError, PermissionError):
                    continue

    return categories


def generate_chrome_cache_report(include_profiles=True):
    """Generates a detailed cache report for Chrome.

    Args:
        include_profiles: Whether to scan all profiles or just the default.

    Returns:
        Dictionary containing the cache report.
    """
    chrome_base = os.path.expanduser('~/Library/Application Support/Google/Chrome')

    if not os.path.exists(chrome_base):
        return {
            "installed": False,
            "profiles": [],
            "total_size": 0,
            "safe_size": 0,
            "categories": {}
        }

    profiles = get_chrome_profiles() if include_profiles else [("Default", os.path.join(chrome_base, "Default"))]
    profile_reports = []
    total_size = 0
    safe_size = 0

    # Get categorized data
    categories = categorize_chrome_cache()

    # Calculate sizes
    for category_type, category_data in categories.items():
        for category_name, items in category_data.items():
            for path, size, item_type in items:
                total_size += size
                if category_type == 'safe':
                    safe_size += size

    # Generate per-profile reports if requested
    if include_profiles:
        for profile_name, profile_path in profiles:
            profile_cache_targets = get_chrome_cache_targets(profile_path)
            profile_size = 0
            cache_dirs = {}

            for cache_name, cache_path in profile_cache_targets.items():
                if cache_name in ["Shader Cache", "GrShader Cache", "Component CRX Cache",
                                 "Screen AI", "Optimization Guide", "Crash Reports", "Crashpad"]:
                    continue  # Skip Chrome-wide caches for individual profiles

                exists = os.path.exists(cache_path)
                size = compute_directory_size(cache_path) if exists else 0
                profile_size += size
                cache_dirs[cache_name] = {"exists": exists, "size": size, "path": cache_path}

            profile_reports.append({
                "name": profile_name,
                "path": profile_path,
                "cache_dirs": cache_dirs,
                "total_size": profile_size
            })

    return {
        "installed": True,
        "chrome_base": chrome_base,
        "profiles": profile_reports,
        "total_size": total_size,
        "safe_size": safe_size,
        "unsafe_size": total_size - safe_size,
        "categories": categories
    }


def scan_chrome_cache(include_profiles=True):
    """
    Scans Chrome cache to generate a report of cleanable files.

    This is a cleaner interface for scanning Chrome cache that matches
    the Unity project scanner pattern.

    Args:
        include_profiles: Boolean indicating whether to scan all profiles.

    Returns:
        A dictionary containing Chrome's cache report.
    """
    return generate_chrome_cache_report(include_profiles=include_profiles)
