#!/usr/bin/env python3
"""
Security Sentinel and Policy Engine for LazyScan.
Implements fail-closed security validation and policy enforcement.
"""

import os
import sys
import json
import hashlib
import re
from pathlib import Path
from typing import Dict, Any, List, Optional

from ..core.errors import SecurityPolicyError
from ..core.logging_config import get_logger, get_console, log_security_event
from .validators import canonicalize_path, is_critical_system_path
from lazyscan.security.audit_encryption_schema import validate_audit_config_schema

logger = get_logger(__name__)
console = get_console()

# Global registry for sentinel instance
_sentinel_instance: Optional["SecuritySentinel"] = None


class SecurityPolicy:
    """Represents a security policy configuration."""

    def __init__(self, policy_data: Dict[str, Any]):
        self.data = policy_data
        self.version = policy_data.get("version", "unknown")
        self.behavior_flags = policy_data.get("behavior_flags", {})
        self.size_limits = policy_data.get("size_limits", {})
        self.allowed_roots = policy_data.get("allowed_roots", {})
        self.deny_patterns = policy_data.get("deny_patterns", {})
        self.audit = policy_data.get("audit", {})

        # Compute policy hash for auditing
        self.hash = self._compute_hash()

        # Validate policy structure
        self._validate()

    def _compute_hash(self) -> str:
        """Compute SHA256 hash of policy data for audit purposes."""
        policy_str = json.dumps(self.data, sort_keys=True)
        return hashlib.sha256(policy_str.encode()).hexdigest()[:12]

    def _validate(self):
        """Validate policy schema and required fields."""
        required_sections = [
            "behavior_flags",
            "size_limits",
            "allowed_roots",
            "deny_patterns",
        ]

        for section in required_sections:
            if section not in self.data:
                raise SecurityPolicyError(f"Policy missing required section: {section}")

        # Validate behavior flags
        required_flags = [
            "require_trash_first",
            "interactive_double_confirm",
            "block_symlinks",
        ]
        for flag in required_flags:
            if flag not in self.behavior_flags:
                raise SecurityPolicyError(
                    f"Policy missing required behavior flag: {flag}"
                )

        # Validate size limits
        required_limits = ["large_directory_threshold_mb", "max_deletion_size_mb"]
        for limit in required_limits:
            if limit not in self.size_limits:
                raise SecurityPolicyError(
                    f"Policy missing required size limit: {limit}"
                )

        # Validate audit configuration if present
        if "audit" in self.data:
            try:
                validate_audit_config_schema(self.audit)
                logger.debug("Audit configuration validation passed")
            except SecurityPolicyError as e:
                raise SecurityPolicyError(f"Audit configuration validation failed: {e}")
            except Exception as e:
                raise SecurityPolicyError(f"Unexpected error validating audit configuration: {e}")

        logger.info(f"Policy validation passed (hash: {self.hash})")

    def get_allowed_roots(self, context: str) -> List[str]:
        """Get allowed roots for a specific context."""
        return self.allowed_roots.get(context, [])

    def get_deny_patterns(self, platform: str) -> List[str]:
        """Get deny patterns for a specific platform."""
        return self.deny_patterns.get(platform, [])

    def should_require_trash_first(self) -> bool:
        """Check if trash-first behavior is required."""
        return self.behavior_flags.get("require_trash_first", True)

    def should_block_symlinks(self) -> bool:
        """Check if symlinks should be blocked."""
        return self.behavior_flags.get("block_symlinks", True)

    def should_double_confirm(self) -> bool:
        """Check if interactive double confirmation is required."""
        return self.behavior_flags.get("interactive_double_confirm", True)

    def get_large_directory_threshold(self) -> float:
        """Get the threshold for considering a directory 'large' (in MB)."""
        return self.size_limits.get("large_directory_threshold_mb", 100)

    def get_max_deletion_size(self) -> float:
        """Get the maximum allowed deletion size (in MB)."""
        return self.size_limits.get("max_deletion_size_mb", 10000)


class SecuritySentinel:
    """
    Central security enforcement point for all destructive operations.
    Implements fail-closed semantics - operations are denied by default.
    """

    def __init__(self, policy: SecurityPolicy):
        self.policy = policy
        self.initialized = False
        self._health_check()
        self.initialized = True

        # Log sentinel activation
        logger.info(
            f"SecuritySentinel initialized (policy_hash: {policy.hash}, "
            f"version: {policy.version})"
        )

    def _health_check(self):
        """Perform health check on sentinel initialization."""
        try:
            # Verify policy is valid
            if not isinstance(self.policy, SecurityPolicy):
                raise SecurityPolicyError("Invalid policy object")

            # Verify critical methods are available
            test_path = Path.home()

            # Check for audit migration needs
            self._check_audit_migration_status()

            # Check deny patterns work
            self._check_deny_patterns(test_path, "macos")

            logger.info("SecuritySentinel health check passed")

        except Exception as e:
            logger.error(f"SecuritySentinel health check failed: {e}")
            raise SecurityPolicyError(f"Sentinel health check failed: {e}")

    def _check_audit_migration_status(self):
        """Check if audit log migration is needed and log warnings."""
        try:
            from lazyscan.security.audit_migration import detect_migration_needed

            migration_needed, results = detect_migration_needed()

            if migration_needed:
                logger.warning(
                    "Audit log migration needed - plaintext logs detected",
                    platforms=[d['platform'] for d in results['directories']],
                    total_plaintext=sum(len(d['plaintext_files']) for d in results['directories'])
                )

                log_security_event(
                    event_type="audit_migration_required",
                    severity="warning",
                    description="Plaintext audit logs detected - migration recommended",
                    platforms=[d['platform'] for d in results['directories']],
                    total_plaintext=sum(len(d['plaintext_files']) for d in results['directories'])
                )
            else:
                logger.debug("Audit migration check passed - no plaintext logs found")

        except Exception as e:
            logger.warning(f"Failed to check audit migration status: {e}")
            # Don't fail initialization for this

    def _check_deny_patterns(self, path: Path, platform: str) -> bool:
        """Check if path matches any deny patterns for the platform."""
        try:
            patterns = self.policy.get_deny_patterns(platform)
            path_str = str(path)

            for pattern in patterns:
                if re.match(pattern, path_str):
                    logger.debug(f"Path {path} matches deny pattern: {pattern}")
                    return True

            return False

        except Exception as e:
            logger.error(f"Error checking deny patterns for {path}: {e}")
            # When in doubt, deny for safety
            return True

    def _get_current_platform(self) -> str:
        """Detect current platform."""
        if sys.platform == "darwin":
            return "macos"
        elif os.name == "nt":
            return "windows"
        else:
            return "linux"

    def guard_delete(
        self, path: Path, context: str = "general", operation_mode: str = "trash"
    ) -> None:
        """
        Guard a deletion operation by validating it against security policy.

        Args:
            path: Path to be deleted (should be canonicalized)
            context: Application context ('unity', 'unreal', 'chrome', etc.)
            operation_mode: Deletion mode ('trash' or 'permanent')

        Raises:
            SecurityPolicyError: If operation violates security policy
        """
        if not self.initialized:
            raise SecurityPolicyError("SecuritySentinel not properly initialized")

        logger.debug(
            f"Guarding delete operation: {path} (context: {context}, mode: {operation_mode})"
        )

        try:
            # Check if path matches platform-specific deny patterns
            platform = self._get_current_platform()
            if self._check_deny_patterns(path, platform):
                raise SecurityPolicyError(
                    f"Path {path} matches security deny pattern for {platform}"
                )

            # Check for critical system paths
            if is_critical_system_path(path):
                if self.policy.behavior_flags.get("fail_on_critical_paths", True):
                    raise SecurityPolicyError(
                        f"Critical system path deletion denied: {path}"
                    )

            # Verify permanent deletion is allowed
            if (
                operation_mode == "permanent"
                and self.policy.should_require_trash_first()
            ):
                raise SecurityPolicyError(
                    "Permanent deletion blocked by policy - use trash mode first"
                )

            # Context-specific validation
            if context != "general":
                allowed_roots = self.policy.get_allowed_roots(context)
                if allowed_roots:
                    from .validators import is_within_allowed_roots

                    root_paths = [canonicalize_path(root) for root in allowed_roots]

                    if not is_within_allowed_roots(path, root_paths):
                        raise SecurityPolicyError(
                            f"Path {path} not within allowed roots for context '{context}'"
                        )

            # Log approval
            if self.policy.audit.get("log_policy_decisions", True):
                logger.info(
                    f"Security approval granted: path={path}, context={context}, "
                    f"mode={operation_mode}, platform={platform}"
                )

        except Exception as e:
            # Log denial
            logger.error(
                f"Security denial: path={path}, context={context}, "
                f"mode={operation_mode}, reason={e}"
            )
            raise


def load_policy(policy_path: Optional[Path] = None) -> SecurityPolicy:
    """
    Load security policy from file or defaults.

    Args:
        policy_path: Optional path to user policy file

    Returns:
        SecurityPolicy: Loaded and validated policy

    Raises:
        SecurityPolicyError: If policy cannot be loaded or is invalid
    """
    try:
        # Try user policy first
        if policy_path and policy_path.exists():
            logger.info(f"Loading user policy from: {policy_path}")
            with open(policy_path, "r") as f:
                policy_data = json.load(f)

        # Try default user config location
        elif not policy_path:
            user_config = Path.home() / ".config" / "lazyscan" / "policy.json"
            if user_config.exists():
                logger.info(f"Loading user policy from: {user_config}")
                with open(user_config, "r") as f:
                    policy_data = json.load(f)
            else:
                # Fall back to bundled defaults
                default_policy_path = Path(__file__).parent / "default_policy.json"
                logger.info(f"Loading default policy from: {default_policy_path}")
                with open(default_policy_path, "r") as f:
                    policy_data = json.load(f)

        else:
            raise SecurityPolicyError(f"Policy file not found: {policy_path}")

        return SecurityPolicy(policy_data)

    except json.JSONDecodeError as e:
        raise SecurityPolicyError(f"Invalid JSON in policy file: {e}")
    except FileNotFoundError as e:
        raise SecurityPolicyError(f"Policy file not found: {e}")
    except Exception as e:
        raise SecurityPolicyError(f"Failed to load policy: {e}")


def initialize_sentinel(policy_path: Optional[Path] = None) -> SecuritySentinel:
    """
    Initialize the global SecuritySentinel instance.
    This MUST be called at application startup.

    Args:
        policy_path: Optional path to custom policy file

    Returns:
        SecuritySentinel: Initialized sentinel instance

    Raises:
        SecurityPolicyError: If initialization fails
    """
    global _sentinel_instance

    try:
        logger.info("Initializing SecuritySentinel...")

        # Load and validate policy
        policy = load_policy(policy_path)

        # Create sentinel instance
        _sentinel_instance = SecuritySentinel(policy)

        # Emit heartbeat log for audit
        logger.info(
            f"SecuritySentinel heartbeat: active=True, policy_hash={policy.hash}, "
            f"version={policy.version}, platform={sys.platform}"
        )

        return _sentinel_instance

    except Exception as e:
        logger.critical(f"SecuritySentinel initialization FAILED: {e}")
        raise SecurityPolicyError(f"Critical security initialization failure: {e}")


def get_sentinel() -> SecuritySentinel:
    """
    Get the global SecuritySentinel instance.

    Returns:
        SecuritySentinel: The initialized sentinel

    Raises:
        SecurityPolicyError: If sentinel not initialized
    """
    if _sentinel_instance is None:
        raise SecurityPolicyError(
            "SecuritySentinel not initialized - call initialize_sentinel() first"
        )

    return _sentinel_instance


def guard_delete(
    path: Path, context: str = "general", operation_mode: str = "trash"
) -> None:
    """
    Convenience function to guard a deletion operation.

    Args:
        path: Path to be deleted
        context: Application context
        operation_mode: Deletion mode ('trash' or 'permanent')

    Raises:
        SecurityPolicyError: If operation violates security policy
    """
    sentinel = get_sentinel()
    sentinel.guard_delete(path, context, operation_mode)


def startup_health_check() -> None:
    """
    Perform mandatory health check at application startup.

    Raises:
        SecurityPolicyError: If health check fails
        SystemExit: If critical failure occurs
    """
    try:
        # Initialize sentinel if not already done
        if _sentinel_instance is None:
            initialize_sentinel()

        # Verify sentinel is working
        sentinel = get_sentinel()

        # Test basic functionality - try to delete the home directory itself
        test_path = Path.home()
        try:
            sentinel.guard_delete(test_path, "general", "trash")
            # Should not reach here for home directory
            raise SecurityPolicyError("Health check failed - critical path not blocked")
        except SecurityPolicyError as e:
            if "Critical system path" in str(e) or "deny pattern" in str(e):
                # Expected - sentinel is working correctly
                logger.info("SecuritySentinel health check: PASSED")
            else:
                # Unexpected error
                raise

    except Exception as e:
        logger.critical(f"SECURITY HEALTH CHECK FAILED: {e}")
        logger.critical("Application cannot start safely - exiting")

        # Log critical security event for audit
        log_security_event(
            event_type="security_health_check_failed",
            severity="critical",
            description=f"Security system health check failed: {e}",
            error_details=str(e),
            startup_failure=True,
        )

        # Use console adapter for user-facing error messages
        console.print_error(f"FATAL: Security system health check failed: {e}")
        console.print_error(
            "LazyScan cannot start safely. Please check logs and configuration."
        )
        sys.exit(1)


def is_sentinel_initialized() -> bool:
    """Check if the sentinel is initialized."""
    return _sentinel_instance is not None and _sentinel_instance.initialized


# Fail-closed check: ensure this module can be imported safely
try:
    # Verify we can load default policy
    _default_policy_path = Path(__file__).parent / "default_policy.json"
    if not _default_policy_path.exists():
        raise SecurityPolicyError(
            "Default policy file missing - security system unavailable"
        )

    # Quick validation of default policy
    with open(_default_policy_path, "r") as f:
        _test_policy = json.load(f)
        SecurityPolicy(_test_policy)  # Will raise if invalid

    logger.debug("Security module import validation passed")

except Exception as e:
    logger.critical(f"Security module validation failed: {e}")
    raise SecurityPolicyError(f"Security system unavailable: {e}")
