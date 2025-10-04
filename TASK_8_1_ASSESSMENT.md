# Task 8.1: Configuration Requirements Assessment for System Cache Management

## Current Platform Cache Module Analysis

### Existing Structure Overview

The current platform cache modules (`lazyscan/platforms/`) provide basic cache path definitions but lack sophisticated cache management features:

#### macOS (`platforms/macos.py`)
- **Current**: Basic path lists for applications (Chrome, Firefox, Safari, etc.)
- **Gaps**: No Homebrew, npm, pip, Docker, or retention policy support
- **Structure**: Simple string lists like `MACOS_CACHE_PATHS`, `FIREFOX_PATHS`, etc.

#### Linux (`platforms/linux.py`)
- **Current**: Basic user cache (`~/.cache`) and apt archives
- **Gaps**: No npm, pip, Docker, or comprehensive package manager support (yum, pacman)
- **Missing**: No `/tmp` aging policies or `/var/cache` variants

#### Windows (`platforms/windows.py`)
- **Current**: Basic user cache and temp directories
- **Gaps**: No Windows Update cache, Prefetch, or comprehensive temp management
- **Missing**: No SoftwareDistribution cleanup or advanced temp policies

### Configuration Schema Analysis

#### Current SecurityConfig (`lazyscan/core/config.py`)
```python
@dataclass
class SecurityConfig:
    enable_backups: bool = True
    backup_dir: str = ""
    confirm_deletions: bool = True
    safe_delete_enabled: bool = True
    max_concurrent_operations: int = 4
```

**Missing Configuration Elements:**
1. **Retention Policies**: No `retention_days` or aging policies
2. **Admin Requirements**: No `requires_admin` flags for privileged operations
3. **Safety Levels**: No granular safety classifications
4. **Platform-Specific Settings**: No OS-specific cache policies

## Required Cache Targets Inventory

### macOS Extensions
1. **Homebrew Cache** (`~/Library/Caches/Homebrew/`)
   - Safety: Safe (user-owned)
   - Admin: No
   - Retention: 30 days (configurable)

2. **npm Cache** (`~/.npm/`)
   - Safety: Safe (user-owned)
   - Admin: No
   - Retention: 90 days (configurable)

3. **pip Cache** (`~/Library/Caches/pip/`)
   - Safety: Safe (user-owned)
   - Admin: No
   - Retention: 90 days (configurable)

4. **Docker Volumes** (Docker Desktop data)
   - Safety: Dangerous (data loss risk)
   - Admin: No (but Docker daemon access)
   - Retention: Manual only (with warnings)

### Linux Extensions
1. **User Cache Directory** (`~/.cache/*`)
   - Safety: Mixed (some safe, some preserve)
   - Admin: No
   - Retention: 30 days (configurable)

2. **APT Archives** (`/var/cache/apt/archives/`)
   - Safety: Safe (re-downloadable)
   - Admin: Yes
   - Retention: 7 days (configurable)

3. **YUM/DNF Cache** (`/var/cache/yum/` or `/var/cache/dnf/`)
   - Safety: Safe (re-downloadable)
   - Admin: Yes
   - Retention: 7 days (configurable)

4. **Pacman Cache** (`/var/cache/pacman/pkg/`)
   - Safety: Safe (re-downloadable)
   - Admin: Yes
   - Retention: 30 days (configurable)

5. **SystemD Journal** (`/var/log/journal/`)
   - Safety: Dangerous (logging loss)
   - Admin: Yes
   - Retention: Manual only

6. **Temporary Files** (`/tmp/`)
   - Safety: Mixed (aging-based cleanup)
   - Admin: No
   - Retention: 7 days (configurable)

### Windows Extensions
1. **Windows Temp** (`%TEMP%`, `%TMP%`)
   - Safety: Safe (temporary files)
   - Admin: No
   - Retention: 7 days (configurable)

2. **Windows Update Cache** (`%WINDIR%\SoftwareDistribution\Download\`)
   - Safety: Dangerous (update integrity)
   - Admin: Yes
   - Retention: Manual only

3. **Prefetch Files** (`%WINDIR%\Prefetch\`)
   - Safety: Safe (performance optimization)
   - Admin: Yes
   - Retention: 30 days (configurable)

4. **Thumbnail Cache** (`%LOCALAPPDATA%\Microsoft\Windows\Explorer\`)
   - Safety: Safe (regenerates)
   - Admin: No
   - Retention: 30 days (configurable)

## Required Configuration Schema Extensions

### New SecurityConfig Fields
```python
@dataclass
class SecurityConfig:
    # Existing fields...
    enable_backups: bool = True
    backup_dir: str = ""
    confirm_deletions: bool = True
    safe_delete_enabled: bool = True
    max_concurrent_operations: int = 4

    # New cache management fields
    cache_retention_days: int = 30
    cache_cleanup_enabled: bool = True
    allow_admin_operations: bool = False
    docker_cleanup_enabled: bool = False
    system_cache_cleanup_enabled: bool = False
```

### New Platform-Specific Config Classes
```python
@dataclass
class CacheTargetConfig:
    enabled: bool = True
    retention_days: Optional[int] = None
    requires_admin: bool = False
    safety_level: str = "safe"  # "safe", "caution", "dangerous"

@dataclass
class PlatformCacheConfig:
    homebrew: CacheTargetConfig = field(default_factory=lambda: CacheTargetConfig(retention_days=30))
    npm: CacheTargetConfig = field(default_factory=lambda: CacheTargetConfig(retention_days=90))
    pip: CacheTargetConfig = field(default_factory=lambda: CacheTargetConfig(retention_days=90))
    docker: CacheTargetConfig = field(default_factory=lambda: CacheTargetConfig(enabled=False, safety_level="dangerous"))
    # ... additional targets
```

### Configuration File Structure (TOML)
```toml
[security]
cache_retention_days = 30
cache_cleanup_enabled = true
allow_admin_operations = false
docker_cleanup_enabled = false
system_cache_cleanup_enabled = false

[cache_targets.macos]
homebrew = { enabled = true, retention_days = 30, requires_admin = false, safety_level = "safe" }
npm = { enabled = true, retention_days = 90, requires_admin = false, safety_level = "safe" }
pip = { enabled = true, retention_days = 90, requires_admin = false, safety_level = "safe" }
docker = { enabled = false, retention_days = null, requires_admin = false, safety_level = "dangerous" }

[cache_targets.linux]
apt = { enabled = true, retention_days = 7, requires_admin = true, safety_level = "safe" }
yum = { enabled = true, retention_days = 7, requires_admin = true, safety_level = "safe" }
pacman = { enabled = true, retention_days = 30, requires_admin = true, safety_level = "safe" }
tmp = { enabled = true, retention_days = 7, requires_admin = false, safety_level = "caution" }

[cache_targets.windows]
temp = { enabled = true, retention_days = 7, requires_admin = false, safety_level = "safe" }
prefetch = { enabled = true, retention_days = 30, requires_admin = true, safety_level = "safe" }
windows_update = { enabled = false, retention_days = null, requires_admin = true, safety_level = "dangerous" }
```

## Implementation Requirements

### 1. CacheTarget Data Structure
```python
@dataclass
class CacheTarget:
    path: Path
    category: str
    requires_admin: bool = False
    retention_days: Optional[int] = None
    safety_level: str = "safe"
    description: str = ""
```

### 2. Platform-Specific Cache Providers
- **macOS**: Extend existing path lists with new CacheTarget objects
- **Linux**: Add comprehensive `/var/cache` and `/tmp` management
- **Windows**: Implement Windows-specific temp and system cache handling

### 3. Retention Policy Engine
- File age calculation functions
- Selective deletion based on retention policies
- Admin privilege checking and warnings

### 4. Safety Classification System
- **Safe**: No data loss risk (caches, temp files)
- **Caution**: Potential performance impact (logs, thumbnails)
- **Dangerous**: Data loss risk (databases, system files)

### 5. Docker Integration
- `docker system prune --volumes` command execution
- Dry-run support with size estimation
- User confirmation for destructive operations

## Migration Considerations

### Backward Compatibility
- Existing platform path lists remain functional
- New CacheTarget system is additive
- Configuration defaults maintain current behavior

### Configuration Migration
- Auto-detect existing cache-related settings
- Provide upgrade path for new configuration schema
- Maintain user preferences across updates

## Testing Requirements

### Unit Tests
- CacheTarget creation and validation
- Platform-specific path resolution
- Retention policy application
- Admin privilege detection

### Integration Tests
- Cross-platform cache discovery
- Retention-based cleanup simulation
- Docker command execution (mocked)
- Configuration loading and validation

### End-to-End Tests
- CLI cache cleanup workflows
- Dry-run output verification
- Backup integration testing
- Admin operation handling

## Next Steps

This assessment provides the foundation for implementing the remaining subtasks in Task 8. The key deliverables are:

1. **Extended SecurityConfig** with cache management fields
2. **CacheTarget data structure** for policy-driven cache management
3. **Platform-specific cache provider updates** with new target definitions
4. **Retention policy engine** for age-based cleanup
5. **Docker integration framework** for container cleanup
6. **Comprehensive test suite** for all new functionality

The implementation should follow the existing LazyScan patterns while providing the flexibility needed for cross-platform cache management.</content>
</xai:function_call">The assessment document has been created. Now let me mark subtask 8.1 as completed and move to the next subtask. The assessment provides a comprehensive analysis of the current state and requirements for extending system cache management across platforms. It identifies all the gaps and outlines the configuration schema extensions needed. This gives us a solid foundation for implementing the remaining subtasks. Let me update the task status. 

<xai:function_call name="task-master-ai_set_task_status">
<parameter name="id">8.1