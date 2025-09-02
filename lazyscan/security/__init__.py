#!/usr/bin/env python3
"""
LazyScan Security Module

Provides comprehensive security guarantees for file operations:
- Path validation and canonicalization
- Safe deletion with multiple safeguards  
- Policy-driven security enforcement
- Global kill switch for emergency stops

Key Components:
- SafeDeleter: Centralized, policy-driven deletion
- SecuritySentinel: Policy enforcement engine
- Path validators: Input sanitization and validation
"""

from .safe_delete import (
    SafeDeleter,
    DeletionMode,
    get_safe_deleter,
    safe_delete
)

from .validators import (
    canonicalize_path,
    is_within_allowed_roots,
    is_symlink_or_reparse,
    is_critical_system_path,
    validate_user_supplied_path,
    validate_unity_path,
    validate_unreal_path,
    validate_chrome_path,
    expand_unreal_engine_paths
)

from .sentinel import (
    SecuritySentinel,
    SecurityPolicy,
    initialize_sentinel,
    get_sentinel,
    guard_delete,
    startup_health_check,
    is_sentinel_initialized,
    load_policy
)

__all__ = [
    # Safe deletion
    'SafeDeleter',
    'DeletionMode',
    'get_safe_deleter',
    'safe_delete',
    
    # Path validation
    'canonicalize_path',
    'is_within_allowed_roots',
    'is_symlink_or_reparse',
    'is_critical_system_path',
    'validate_user_supplied_path',
    'validate_unity_path',
    'validate_unreal_path',
    'validate_chrome_path',
    'expand_unreal_engine_paths',
    
    # Security sentinel
    'SecuritySentinel',
    'SecurityPolicy', 
    'initialize_sentinel',
    'get_sentinel',
    'guard_delete',
    'startup_health_check',
    'is_sentinel_initialized',
    'load_policy'
]
