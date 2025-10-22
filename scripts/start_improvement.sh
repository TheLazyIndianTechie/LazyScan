#!/bin/bash

# LazyScan Improvement Plan - Quick Start Script
# This script begins implementing Step 1: Centralize Safe Deletion + Global Kill Switch

set -e

echo "🚀 Starting LazyScan Improvement Plan - Step 1: Safe Deletion Module"
echo "=================================================================="

# Create directory structure
echo "📁 Creating security module directories..."
mkdir -p lazyscan/security
mkdir -p lazyscan/core
mkdir -p tests/security

# Create __init__.py files
touch lazyscan/__init__.py
touch lazyscan/security/__init__.py
touch lazyscan/core/__init__.py

echo "✅ Directory structure created"

# Create the SafeDeleter module template
echo "🔒 Creating SafeDeleter module template..."
cat > lazyscan/security/safe_delete.py << 'EOF'
#!/usr/bin/env python3
"""
Safe deletion module with fail-closed security guarantees.
Eliminates direct file deletion risks with policy-driven approach.
"""

import os
import sys
from pathlib import Path
from typing import Literal, Optional
from enum import Enum
import logging

try:
    import send2trash
except ImportError:
    send2trash = None

logger = logging.getLogger(__name__)


class DeletionSafetyError(Exception):
    """Raised when deletion is blocked for safety reasons."""
    pass


class DeletionMode(Enum):
    TRASH = "trash"
    PERMANENT = "permanent"


class SafeDeleter:
    """
    Centralized, policy-driven file deletion with security safeguards.

    Key features:
    - Global kill switch via LAZYSCAN_DISABLE_DELETIONS=1
    - Trash-first deletion by default
    - Path validation before any operation
    - Structured logging of all decisions
    - Two-step confirmation for large directories
    """

    def __init__(self):
        self._kill_switch_enabled = os.getenv("LAZYSCAN_DISABLE_DELETIONS", "0") == "1"
        if self._kill_switch_enabled:
            logger.warning("🛑 Global kill switch enabled - all deletions disabled")

    def delete(
        self,
        path: Path,
        mode: DeletionMode = DeletionMode.TRASH,
        dry_run: bool = True,
        force: bool = False
    ) -> bool:
        """
        Safely delete a file or directory with comprehensive checks.

        Args:
            path: Path to delete (will be canonicalized)
            mode: DeletionMode.TRASH (default) or DeletionMode.PERMANENT
            dry_run: If True, log what would be deleted but don't actually delete
            force: If True, skip interactive confirmations (dangerous!)

        Returns:
            bool: True if deletion was successful or would succeed (dry_run)

        Raises:
            DeletionSafetyError: If deletion is blocked by security checks
        """

        # Check global kill switch first
        if self._kill_switch_enabled:
            raise DeletionSafetyError(
                "Global deletion kill switch is enabled (LAZYSCAN_DISABLE_DELETIONS=1). "
                "All destructive operations are blocked."
            )

        # Canonicalize and validate path
        try:
            canonical_path = path.resolve(strict=False)
        except Exception as e:
            raise DeletionSafetyError(f"Cannot resolve path {path}: {e}")

        # Log the deletion attempt
        logger.info(
            "Deletion requested",
            extra={
                "path": str(canonical_path),
                "mode": mode.value,
                "dry_run": dry_run,
                "force": force
            }
        )

        # Security checks
        self._validate_deletion_safety(canonical_path)

        if dry_run:
            logger.info(f"DRY RUN: Would delete {canonical_path} using {mode.value} mode")
            return True

        # Actual deletion logic would go here
        if mode == DeletionMode.TRASH:
            return self._delete_to_trash(canonical_path, force=force)
        else:
            return self._delete_permanent(canonical_path, force=force)

    def _validate_deletion_safety(self, path: Path) -> None:
        """
        Validate that the path is safe to delete.

        Raises:
            DeletionSafetyError: If path fails safety checks
        """

        # Check if path exists
        if not path.exists():
            logger.warning(f"Path does not exist: {path}")
            return  # Not an error - already "deleted"

        # Critical path checks
        if self._is_critical_system_path(path):
            raise DeletionSafetyError(
                f"Attempted to delete critical system path: {path}. "
                "This operation is blocked for safety."
            )

        # Symlink/junction checks
        if path.is_symlink():
            raise DeletionSafetyError(
                f"Attempted to delete symlink: {path}. "
                "Symlink deletion is blocked to prevent unexpected behavior."
            )

        logger.debug(f"Path validation passed for: {path}")

    def _is_critical_system_path(self, path: Path) -> bool:
        """Check if path is a critical system directory that should never be deleted."""

        critical_paths = [
            Path.home(),  # User home directory
            Path("/"),    # Root directory (Unix)
            Path("C:\\"), # C: drive root (Windows)
            Path("/System"), # macOS system directory
            Path("/usr"),    # Unix system directories
            Path("/var"),
            Path("/etc"),
            Path("/boot"),
        ]

        # Check if path is or is parent of any critical path
        for critical in critical_paths:
            try:
                if path.samefile(critical) or critical.is_relative_to(path):
                    return True
            except (OSError, ValueError):
                # Handle paths that don't exist or permission errors
                continue

        return False

    def _delete_to_trash(self, path: Path, force: bool = False) -> bool:
        """Delete path to trash/recycle bin."""

        if send2trash is None:
            raise DeletionSafetyError(
                "send2trash library not available. Cannot safely delete to trash. "
                "Install with: pip install send2trash"
            )

        try:
            send2trash.send2trash(str(path))
            logger.info(f"Successfully moved to trash: {path}")
            return True
        except Exception as e:
            logger.error(f"Failed to move to trash: {path}, error: {e}")
            raise DeletionSafetyError(f"Trash deletion failed: {e}")

    def _delete_permanent(self, path: Path, force: bool = False) -> bool:
        """Permanently delete path (dangerous!)."""

        if not force and sys.stdin.isatty():
            # Interactive confirmation required
            print(f"⚠️  PERMANENT DELETION WARNING")
            print(f"   Path: {path}")
            print(f"   This operation CANNOT be undone!")

            response = input("   Type 'DELETE' to confirm: ").strip()
            if response != "DELETE":
                print("   Deletion cancelled.")
                logger.info(f"Permanent deletion cancelled by user: {path}")
                return False

        # TODO: Implement permanent deletion logic
        logger.warning(f"PERMANENT DELETION NOT YET IMPLEMENTED: {path}")
        raise NotImplementedError("Permanent deletion not yet implemented for safety")


# Global instance
_safe_deleter = None

def get_safe_deleter() -> SafeDeleter:
    """Get the global SafeDeleter instance."""
    global _safe_deleter
    if _safe_deleter is None:
        _safe_deleter = SafeDeleter()
    return _safe_deleter


def safe_delete(path: Path, **kwargs) -> bool:
    """Convenience function for safe deletion."""
    return get_safe_deleter().delete(path, **kwargs)
EOF

echo "✅ SafeDeleter module created"

# Create error definitions
echo "🚨 Creating error definitions..."
cat > lazyscan/core/errors.py << 'EOF'
#!/usr/bin/env python3
"""
Custom exception hierarchy for LazyScan.
Provides typed exceptions to replace generic exception handling.
"""


class LazyScanError(Exception):
    """Base exception for all LazyScan errors."""
    pass


class PathValidationError(LazyScanError):
    """Raised when path validation fails."""
    pass


class DeletionSafetyError(LazyScanError):
    """Raised when deletion is blocked for safety reasons."""
    pass


class SecurityPolicyError(LazyScanError):
    """Raised when security policy validation fails."""
    pass


class UnsupportedPlatformError(LazyScanError):
    """Raised when operation is not supported on current platform."""
    pass


class DiscoveryError(LazyScanError):
    """Raised when project discovery fails."""
    pass


class ConfigError(LazyScanError):
    """Raised when configuration is invalid."""
    pass


class UserAbortedError(LazyScanError):
    """Raised when user cancels an operation."""
    pass
EOF

echo "✅ Error definitions created"

# Create basic test for SafeDeleter
echo "🧪 Creating basic test for SafeDeleter..."
cat > tests/security/test_safe_delete.py << 'EOF'
#!/usr/bin/env python3
"""
Tests for SafeDeleter module.
"""

import os
import pytest
from pathlib import Path
from unittest.mock import patch

from lazyscan.security.safe_delete import SafeDeleter, DeletionSafetyError, DeletionMode


class TestSafeDeleter:

    def setup_method(self):
        """Setup for each test method."""
        self.deleter = SafeDeleter()

    def test_kill_switch_blocks_deletion(self):
        """Test that global kill switch blocks all deletions."""
        with patch.dict(os.environ, {"LAZYSCAN_DISABLE_DELETIONS": "1"}):
            deleter = SafeDeleter()
            test_path = Path("/tmp/test")

            with pytest.raises(DeletionSafetyError) as exc_info:
                deleter.delete(test_path, dry_run=False)

            assert "kill switch" in str(exc_info.value).lower()

    def test_dry_run_mode(self):
        """Test that dry run mode doesn't actually delete."""
        test_path = Path("/tmp/nonexistent")

        # Should return True for dry run without actually doing anything
        result = self.deleter.delete(test_path, dry_run=True)
        assert result is True

    def test_critical_path_rejection(self):
        """Test that critical system paths are rejected."""
        critical_paths = [
            Path.home(),
            Path("/"),
            Path("C:\\") if os.name == 'nt' else Path("/usr"),
        ]

        for critical_path in critical_paths:
            if critical_path.exists():
                with pytest.raises(DeletionSafetyError) as exc_info:
                    self.deleter.delete(critical_path, dry_run=False)

                assert "critical system path" in str(exc_info.value).lower()

    def test_symlink_rejection(self, tmp_path):
        """Test that symlinks are rejected."""
        # Create a test file and symlink to it
        test_file = tmp_path / "test_file.txt"
        test_file.write_text("test content")

        test_symlink = tmp_path / "test_symlink"
        test_symlink.symlink_to(test_file)

        with pytest.raises(DeletionSafetyError) as exc_info:
            self.deleter.delete(test_symlink, dry_run=False)

        assert "symlink" in str(exc_info.value).lower()


if __name__ == "__main__":
    pytest.main([__file__])
EOF

echo "✅ Basic tests created"

# Create requirements for the improvement
echo "📦 Creating requirements file..."
cat > requirements-improvement.txt << 'EOF'
# Dependencies for LazyScan improvement plan
send2trash>=1.8.0
platformdirs>=3.0.0
pytest>=7.0.0
pytest-cov>=4.0.0
hypothesis>=6.0.0

# Development tools
ruff>=0.0.280
black>=23.0.0
mypy>=1.0.0
pre-commit>=3.0.0
EOF

# Create ast-grep usage examples script
echo "🔍 Creating ast-grep usage examples..."
cat > scripts/analyze_patterns.sh << 'EOF'
#!/bin/bash

# ast-grep usage examples for LazyScan improvement

echo "🔍 Analyzing dangerous file operations..."
echo "======================================="

echo "1. Finding shutil.rmtree calls:"
ast-grep --pattern 'shutil.rmtree($_)' --lang python . || echo "No matches found"

echo -e "\n2. Finding os.remove calls:"
ast-grep --pattern 'os.remove($_)' --lang python . || echo "No matches found"

echo -e "\n3. Finding print statements:"
ast-grep --pattern 'print($_)' --lang python . | wc -l | xargs echo "Total print statements found:"

echo -e "\n4. Finding input calls (potential validation points):"
ast-grep --pattern 'input($_)' --lang python . || echo "No matches found"

echo -e "\n5. Finding glob.glob calls:"
ast-grep --pattern 'glob.glob($_)' --lang python . || echo "No matches found"

echo -e "\n6. Finding try-except blocks:"
ast-grep --pattern 'try: $$$' --lang python lazyscan.py | grep "try:" | wc -l | xargs echo "Try blocks found in main file:"

echo -e "\n📊 Analysis complete! Check the patterns above for improvement opportunities."
EOF

chmod +x scripts/analyze_patterns.sh

echo "✅ Analysis script created"

# Create a simple migration checklist
echo "📋 Creating implementation checklist..."
cat > MIGRATION_CHECKLIST.md << 'EOF'
# LazyScan Improvement Implementation Checklist

## Phase 1: Critical Security Foundation ⚠️

### Step 1: Safe Deletion Module
- [x] Create SafeDeleter module template
- [x] Implement global kill switch check
- [x] Add basic path validation
- [ ] Add comprehensive critical path detection
- [ ] Implement trash-first deletion with send2trash
- [ ] Add two-step confirmation for large directories
- [ ] Replace all direct shutil.rmtree/os.remove calls
- [ ] Add comprehensive tests

### Step 2: Path Validation Library
- [ ] Create validators.py module
- [ ] Implement canonicalize_path() function
- [ ] Add is_within_allowed_roots() validation
- [ ] Add symlink/junction detection
- [ ] Add Windows reserved name detection
- [ ] Create allowed roots registry
- [ ] Add Unreal Engine non-default path support

### Step 3: Security Sentinel
- [ ] Create sentinel.py module
- [ ] Implement policy loading and validation
- [ ] Add fail-closed initialization
- [ ] Create default policy.json
- [ ] Wire SafeDeleter to require sentinel approval
- [ ] Add sentinel heartbeat logging

## Verification Commands

### Test the SafeDeleter:
```bash
python -c "from lazyscan.security.safe_delete import safe_delete; from pathlib import Path; safe_delete(Path('/tmp/test'), dry_run=True)"
```

### Test kill switch:
```bash
LAZYSCAN_DISABLE_DELETIONS=1 python -c "from lazyscan.security.safe_delete import SafeDeleter; SafeDeleter().delete(Path('/tmp/test'), dry_run=False)"
```

### Run basic tests:
```bash
python -m pytest tests/security/test_safe_delete.py -v
```

### Analyze current patterns:
```bash
./scripts/analyze_patterns.sh
```

## Next Steps

1. Install dependencies:
   ```bash
   pip install -r requirements-improvement.txt
   ```

2. Run the analysis script to see current state:
   ```bash
   ./scripts/analyze_patterns.sh
   ```

3. Test the SafeDeleter module:
   ```bash
   python -m pytest tests/security/ -v
   ```

4. Begin replacing direct deletion calls:
   ```bash
   # Find calls to replace
   ast-grep --pattern 'shutil.rmtree($_)' --lang python .

   # Use interactive replacement
   ast-grep --pattern 'shutil.rmtree($X)' --rewrite 'get_safe_deleter().delete(Path($X), mode=DeletionMode.PERMANENT, dry_run=False)' --interactive
   ```

5. Continue with remaining steps from IMPROVEMENT_PLAN.md
EOF

echo "✅ Migration checklist created"

echo ""
echo "🎉 Step 1 foundation has been created!"
echo "================================================"
echo ""
echo "📁 Files created:"
echo "  - lazyscan/security/safe_delete.py (SafeDeleter module)"
echo "  - lazyscan/core/errors.py (Custom exceptions)"
echo "  - tests/security/test_safe_delete.py (Basic tests)"
echo "  - requirements-improvement.txt (Dependencies)"
echo "  - scripts/analyze_patterns.sh (Analysis tool)"
echo "  - MIGRATION_CHECKLIST.md (Implementation guide)"
echo ""
echo "🚀 Next actions:"
echo "  1. Install dependencies: pip install -r requirements-improvement.txt"
echo "  2. Run analysis: ./scripts/analyze_patterns.sh"
echo "  3. Run tests: python -m pytest tests/security/ -v"
echo "  4. Follow MIGRATION_CHECKLIST.md for detailed steps"
echo "  5. Review IMPROVEMENT_PLAN.md for the complete roadmap"
echo ""
echo "⚠️  Remember: This creates the foundation. You still need to:"
echo "  - Replace all direct file deletion calls with SafeDeleter"
echo "  - Implement comprehensive path validation"
echo "  - Add the security sentinel and policy engine"
echo ""
echo "✅ Ready to begin the improvement journey!"
EOF

chmod +x scripts/start_improvement.sh

<function_calls>
<invoke name="run_command">
<parameter name="command">chmod +x scripts/start_improvement.sh
