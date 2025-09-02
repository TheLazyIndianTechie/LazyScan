# Logging Migration Guide

This guide provides instructions for migrating from print statements to structured logging in LazyScan.

## Overview

LazyScan now uses a comprehensive structured logging framework that provides:

- **JSON structured logging** for audit trails and machine parsing
- **Human-readable console logging** with optional colors
- **Context management** for operation tracking
- **Console adapter functions** to replace print statements
- **Security event logging** for audit compliance
- **Performance profiling** integrated with logging

## Quick Migration

### 1. Import the Console Adapter

Replace print statements by importing and using the console adapter:

```python
# Old approach
print("✅ Operation completed successfully")
print("⚠️ Warning: Cache files are in use")
print("❌ Error: Failed to access directory")

# New approach
from lazyscan.core.logging_config import get_console

console = get_console()
console.print_success("Operation completed successfully")
console.print_warning("Warning: Cache files are in use")
console.print_error("Error: Failed to access directory")
```

### 2. Use Structured Logging for Internal Operations

For detailed logging with context:

```python
# Old approach
print(f"Scanning {path} for Unity caches...")
print(f"Found {count} cache directories totaling {size_mb}MB")

# New approach
from lazyscan.core.logging_config import get_logger, log_context

logger = get_logger(__name__)

with log_context(operation="unity_scan", target_path=str(path)):
    logger.info("Starting Unity cache scan", 
               path=str(path),
               scan_type="discovery")
    
    logger.info("Cache scan completed", 
               cache_count=count,
               total_size_mb=size_mb,
               scan_duration_seconds=duration)
```

## Migration Patterns

### Pattern 1: User-Facing Messages

**Before:**
```python
print("🎯 LazyScan - Unity Cache Cleaner")
print("=" * 50)
print(f"Scanning Unity projects in {unity_path}")
```

**After:**
```python
from lazyscan.core.logging_config import get_console

console = get_console()
console.print("🎯 LazyScan - Unity Cache Cleaner")
console.print("=" * 50)
console.print_info(f"Scanning Unity projects in {unity_path}")
```

### Pattern 2: Error Messages

**Before:**
```python
print(f"❌ Error: Could not access {path}")
print("   Check permissions and try again")
```

**After:**
```python
console.print_error(f"Error: Could not access {path}")
console.print_error("   Check permissions and try again")

# Or with structured logging for better tracking:
logger.error("Path access failed", 
            path=str(path),
            error_type="permission_denied",
            operation="scan_directory")
```

### Pattern 3: Progress and Status Updates

**Before:**
```python
print(f"[{current}/{total}] Processing {project_name}...")
print(f"  Found {cache_size}MB in cache directory")
```

**After:**
```python
console.print(f"[{current}/{total}] Processing {project_name}...")
console.print(f"  Found {cache_size}MB in cache directory")

# With structured logging for metrics:
logger.info("Processing Unity project",
           project_name=project_name,
           progress=f"{current}/{total}",
           cache_size_mb=cache_size,
           project_path=str(project_path))
```

### Pattern 4: Confirmation Prompts

**Before:**
```python
print(f"⚠️  WARNING: About to delete {size_mb}MB of cache data")
print(f"   Directories: {len(directories)}")
response = input("Continue? (y/N): ")
```

**After:**
```python
console.print_warning(f"WARNING: About to delete {size_mb}MB of cache data")
console.print_warning(f"   Directories: {len(directories)}")
response = input("Continue? (y/N): ")

# Log the user decision for audit:
logger.info("User confirmation requested",
           operation="cache_deletion",
           size_mb=size_mb,
           directory_count=len(directories),
           user_response=response)
```

### Pattern 5: Security-Related Events

**Before:**
```python
print(f"🛡️  Security: Blocking deletion of {path}")
print(f"   Reason: {reason}")
```

**After:**
```python
from lazyscan.core.logging_config import log_security_event

console.print_warning(f"Security: Blocking deletion of {path}")
console.print_warning(f"   Reason: {reason}")

# Log to audit trail:
log_security_event(
    event_type='deletion_blocked',
    severity='warning',
    description=f'Deletion blocked for security: {reason}',
    path=str(path),
    reason=reason,
    operation=current_operation
)
```

## Console Adapter Methods

The console adapter provides these methods:

- `console.print(*args)` - Normal output (like print)
- `console.print_success(*args)` - Success messages (green, with ✅)
- `console.print_error(*args)` - Error messages (red, with ❌)  
- `console.print_warning(*args)` - Warning messages (yellow, with ⚠️)
- `console.print_info(*args)` - Info messages (cyan, with ℹ️)
- `console.print_debug(*args)` - Debug messages (gray, with 🔍)

## Structured Logger Methods

The structured logger provides these methods with automatic context:

- `logger.debug(message, **context)` - Debug information
- `logger.info(message, **context)` - General information
- `logger.warning(message, **context)` - Warning conditions
- `logger.error(message, **context)` - Error conditions
- `logger.critical(message, **context)` - Critical failures

## Context Management

Use context managers to automatically add context to all log entries:

```python
from lazyscan.core.logging_config import log_context

with log_context(operation="unity_cleanup", user_id="john", session_id="abc123"):
    logger.info("Starting cleanup operation")  # Includes context
    console.print_success("Cleanup completed")  # Includes context
    # All logs in this block will have operation, user_id, session_id
```

## Migration Checklist

For each file being migrated:

1. **Import the console adapter:**
   ```python
   from lazyscan.core.logging_config import get_console
   console = get_console()
   ```

2. **Import structured logger if needed:**
   ```python
   from lazyscan.core.logging_config import get_logger
   logger = get_logger(__name__)
   ```

3. **Replace print statements:**
   - `print(message)` → `console.print(message)`
   - Error messages → `console.print_error(message)`
   - Success messages → `console.print_success(message)`
   - Warning messages → `console.print_warning(message)`

4. **Add structured logging for operations:**
   - Use `logger.info()` for operation progress
   - Use `logger.error()` for error tracking
   - Use `log_context()` for operation grouping

5. **Add security event logging where needed:**
   - Use `log_security_event()` for security-related actions
   - Use `log_deletion_event()` for file deletions

## Testing the Migration

After migrating a module, test that:

1. **Console output still works:**
   ```bash
   python -m lazyscan --dry-run
   ```

2. **Structured logging is working:**
   ```bash
   python -m lazyscan --log-level=DEBUG --log-format=json
   ```

3. **Audit logging is captured:**
   ```bash
   # Check that security events create audit entries
   tail -f logs/lazyscan_audit.log
   ```

## Configuration

Users can configure logging behavior:

```python
from lazyscan.core.logging_config import setup_logging, configure_audit_logging

# Setup main logging
setup_logging(
    console_format='human',  # or 'json'
    log_level='INFO',        # DEBUG, INFO, WARNING, ERROR, CRITICAL
    log_file='lazyscan.log', # Optional file output
    enable_colors=True       # Colorize console output
)

# Setup audit logging
configure_audit_logging(
    audit_file='audit.log',
    audit_level='INFO'
)
```

## Benefits of Migration

After migration, LazyScan will have:

1. **Consistent logging format** across all components
2. **Machine-readable audit trails** for compliance
3. **Better debugging** with structured context
4. **Flexible output formats** (human-readable or JSON)
5. **Centralized security event tracking**
6. **Performance metrics** integrated with logging
7. **Context propagation** across operations

## Example: Complete Migration

**Before (old code):**
```python
def scan_unity_caches(unity_path):
    print(f"🎯 Scanning Unity caches in {unity_path}")
    
    try:
        projects = find_unity_projects(unity_path)
        print(f"✅ Found {len(projects)} Unity projects")
        
        total_size = 0
        for i, project in enumerate(projects, 1):
            print(f"[{i}/{len(projects)}] Scanning {project.name}")
            size = calculate_cache_size(project)
            total_size += size
            print(f"  Cache size: {size}MB")
            
        print(f"🎯 Total cache size: {total_size}MB")
        return projects, total_size
        
    except Exception as e:
        print(f"❌ Error during scan: {e}")
        return [], 0
```

**After (migrated code):**
```python
from lazyscan.core.logging_config import get_console, get_logger, log_context
from lazyscan.core.errors import handle_exception

def scan_unity_caches(unity_path):
    console = get_console()
    logger = get_logger(__name__)
    
    with log_context(operation="unity_cache_scan", target_path=str(unity_path)):
        console.print_info(f"Scanning Unity caches in {unity_path}")
        logger.info("Unity cache scan started", target_path=str(unity_path))
        
        try:
            projects = find_unity_projects(unity_path)
            console.print_success(f"Found {len(projects)} Unity projects")
            logger.info("Unity projects discovered", 
                       project_count=len(projects),
                       discovery_method="filesystem_scan")
            
            total_size = 0
            for i, project in enumerate(projects, 1):
                console.print(f"[{i}/{len(projects)}] Scanning {project.name}")
                
                size = calculate_cache_size(project)
                total_size += size
                
                console.print(f"  Cache size: {size}MB")
                logger.debug("Project cache analyzed",
                           project_name=project.name,
                           project_path=str(project.path),
                           cache_size_mb=size,
                           progress=f"{i}/{len(projects)}")
                
            console.print_success(f"Total cache size: {total_size}MB")
            logger.info("Unity cache scan completed",
                       total_projects=len(projects),
                       total_size_mb=total_size,
                       scan_successful=True)
            
            return projects, total_size
            
        except Exception as e:
            console.print_error(f"Error during scan: {e}")
            handle_exception(e, logger, "unity_cache_scan")
            return [], 0
```

This migration provides better tracking, audit trails, and maintainability while preserving the user experience.
