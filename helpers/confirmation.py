#!/usr/bin/env python3
"""
Confirmation Dialog System for LazyScan

This module provides comprehensive confirmation dialogs with multiple security
levels to prevent accidental deletion of critical user data.

Author: Security Enhancement for LazyScan
Version: 1.0.0
"""

import os
import sys
import time
import random
import string
from typing import List, Dict, Optional, Tuple
from enum import Enum
from dataclasses import dataclass
from .security import validate_paths, sanitize_input

class RiskLevel(Enum):
    """Risk levels for different operations"""
    LOW = "low"          # Individual cache files
    MEDIUM = "medium"    # Cache directories
    HIGH = "high"        # Multiple directories or large amounts
    CRITICAL = "critical" # System-wide operations

@dataclass
class OperationSummary:
    """Summary of operation to be performed"""
    operation_type: str
    target_paths: List[str]
    total_size: int
    file_count: int
    risk_level: RiskLevel
    warnings: List[str]
    estimated_time: float

class ConfirmationDialog:
    """
    Multi-level confirmation system with security safeguards.
    """

    def __init__(self, enable_safety_delays: bool = True):
        self.enable_safety_delays = enable_safety_delays
        self.confirmation_history = []

    def get_operation_confirmation(self, summary: OperationSummary) -> bool:
        """
        Get user confirmation for an operation based on risk level.

        Args:
            summary: OperationSummary containing operation details

        Returns:
            bool: True if user confirms, False otherwise
        """
        print("\n" + "="*80)
        print("🔒 LAZYSCAN SECURITY CONFIRMATION")
        print("="*80)

        # Display operation summary
        self._display_operation_summary(summary)

        # Apply risk-level specific confirmation
        if summary.risk_level == RiskLevel.LOW:
            return self._get_low_risk_confirmation(summary)
        elif summary.risk_level == RiskLevel.MEDIUM:
            return self._get_medium_risk_confirmation(summary)
        elif summary.risk_level == RiskLevel.HIGH:
            return self._get_high_risk_confirmation(summary)
        elif summary.risk_level == RiskLevel.CRITICAL:
            return self._get_critical_risk_confirmation(summary)

        return False

    def _display_operation_summary(self, summary: OperationSummary) -> None:
        """Display detailed operation summary"""
        print(f"\n📋 Operation: {summary.operation_type}")
        print(f"🎯 Risk Level: {summary.risk_level.value.upper()}")
        print(f"📁 Targets: {len(summary.target_paths)} path(s)")
        print(f"📊 Total Size: {self._format_size(summary.total_size)}")
        print(f"📄 File Count: {summary.file_count:,} files")
        print(f"⏱️  Estimated Time: {summary.estimated_time:.1f} seconds")

        # Show warnings if any
        if summary.warnings:
            print("\n⚠️  WARNINGS:")
            for warning in summary.warnings:
                print(f"   • {warning}")

        # Show first few paths
        print("\n📂 Target Paths:")
        for i, path in enumerate(summary.target_paths[:5]):
            print(f"   {i+1}. {path}")

        if len(summary.target_paths) > 5:
            print(f"   ... and {len(summary.target_paths) - 5} more paths")

    def _get_low_risk_confirmation(self, summary: OperationSummary) -> bool:
        """Simple confirmation for low-risk operations"""
        print("\n✅ This is a LOW RISK operation.")

        while True:
            response = input("\nProceed with deletion? [y/N]: ").strip().lower()
            response = sanitize_input(response, "selection")

            if response in ['y', 'yes']:
                return True
            elif response in ['n', 'no', '']:
                print("❌ Operation cancelled by user.")
                return False
            else:
                print("Please enter 'y' for yes or 'n' for no.")

    def _get_medium_risk_confirmation(self, summary: OperationSummary) -> bool:
        """Enhanced confirmation for medium-risk operations"""
        print("\n⚠️  This is a MEDIUM RISK operation.")
        print("Files will be permanently deleted and cannot be easily recovered.")

        # Safety delay
        if self.enable_safety_delays:
            print("\n⏳ Safety delay: 3 seconds...")
            time.sleep(3)

        # First confirmation
        while True:
            response = input("\nDo you want to proceed? [y/N]: ").strip().lower()
            response = sanitize_input(response, "selection")

            if response in ['y', 'yes']:
                break
            elif response in ['n', 'no', '']:
                print("❌ Operation cancelled by user.")
                return False
            else:
                print("Please enter 'y' for yes or 'n' for no.")

        # Second confirmation
        print("\n🔄 Second confirmation required for medium-risk operations.")
        while True:
            response = input("Are you absolutely sure? [y/N]: ").strip().lower()
            response = sanitize_input(response, "selection")

            if response in ['y', 'yes']:
                return True
            elif response in ['n', 'no', '']:
                print("❌ Operation cancelled by user.")
                return False
            else:
                print("Please enter 'y' for yes or 'n' for no.")

    def _get_high_risk_confirmation(self, summary: OperationSummary) -> bool:
        """Strict confirmation for high-risk operations"""
        print("\n🚨 This is a HIGH RISK operation!")
        print("This operation will delete a large amount of data.")
        print("Files will be PERMANENTLY DELETED and cannot be recovered without backups.")

        # Safety delay
        if self.enable_safety_delays:
            print("\n⏳ Mandatory safety delay: 5 seconds...")
            time.sleep(5)

        # Show detailed breakdown
        print("\n📊 Detailed Breakdown:")
        size_gb = summary.total_size / (1024**3)
        if size_gb > 1:
            print(f"   💾 Total size: {size_gb:.2f} GB")
        else:
            print(f"   💾 Total size: {summary.total_size / (1024**2):.2f} MB")

        print(f"   📄 Files to delete: {summary.file_count:,}")
        print(f"   📁 Directories: {len(summary.target_paths)}")

        # First confirmation
        while True:
            response = input("\nDo you understand the risks and want to proceed? [y/N]: ").strip().lower()
            response = sanitize_input(response, "selection")

            if response in ['y', 'yes']:
                break
            elif response in ['n', 'no', '']:
                print("❌ Operation cancelled by user.")
                return False
            else:
                print("Please enter 'y' for yes or 'n' for no.")

        # Type confirmation
        confirmation_word = "DELETE"
        print(f"\n⌨️  Type '{confirmation_word}' to confirm:")
        while True:
            response = input(f"Enter '{confirmation_word}': ").strip()
            response = sanitize_input(response, "selection")

            if response == confirmation_word:
                break
            elif response.lower() in ['cancel', 'quit', 'exit']:
                print("❌ Operation cancelled by user.")
                return False
            else:
                print(f"Please type exactly '{confirmation_word}' or 'cancel' to abort.")

        # Final confirmation
        print("\n🔄 Final confirmation required.")
        while True:
            response = input("This is your last chance. Proceed with deletion? [y/N]: ").strip().lower()
            response = sanitize_input(response, "selection")

            if response in ['y', 'yes']:
                return True
            elif response in ['n', 'no', '']:
                print("❌ Operation cancelled by user.")
                return False
            else:
                print("Please enter 'y' for yes or 'n' for no.")

    def _get_critical_risk_confirmation(self, summary: OperationSummary) -> bool:
        """Maximum security confirmation for critical operations"""
        print("\n🚨🚨🚨 CRITICAL RISK OPERATION! 🚨🚨🚨")
        print("This operation affects system-wide or critical directories.")
        print("EXTREME CAUTION REQUIRED - DATA LOSS MAY BE IRREVERSIBLE!")

        # Extended safety delay
        if self.enable_safety_delays:
            print("\n⏳ Mandatory safety delay: 10 seconds...")
            for i in range(10, 0, -1):
                print(f"   {i}...", end="", flush=True)
                time.sleep(1)
            print("\n")

        # Show all paths for critical operations
        print("\n📂 ALL TARGET PATHS:")
        for i, path in enumerate(summary.target_paths, 1):
            print(f"   {i:2d}. {path}")

        # Path validation check
        print("\n🔍 Performing security validation...")
        validation_results = validate_paths(summary.target_paths)
        unsafe_paths = [path for path, (is_safe, _) in validation_results.items() if not is_safe]

        if unsafe_paths:
            print("\n❌ SECURITY VALIDATION FAILED!")
            print("The following paths failed security validation:")
            for path in unsafe_paths:
                _, reason = validation_results[path]
                print(f"   • {path}: {reason}")
            print("\n🛑 Operation BLOCKED for security reasons.")
            return False

        print("✅ Security validation passed.")

        # Generate random confirmation code
        confirmation_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

        print(f"\n🔐 Security Code: {confirmation_code}")
        print("You must enter this code exactly to proceed.")

        attempts = 0
        max_attempts = 3

        while attempts < max_attempts:
            response = input(f"\nEnter security code: ").strip()
            response = sanitize_input(response, "selection")

            if response == confirmation_code:
                break
            elif response.lower() in ['cancel', 'quit', 'exit']:
                print("❌ Operation cancelled by user.")
                return False
            else:
                attempts += 1
                remaining = max_attempts - attempts
                if remaining > 0:
                    print(f"❌ Incorrect code. {remaining} attempts remaining.")
                else:
                    print("❌ Maximum attempts exceeded. Operation cancelled.")
                    return False

        # Final warning and confirmation
        print("\n⚠️  FINAL WARNING:")
        print("This operation will PERMANENTLY DELETE the specified files and directories.")
        print("There is NO UNDO for this operation.")
        print("Make sure you have backups of any important data.")

        while True:
            response = input("\nI understand the risks and want to proceed [y/N]: ").strip().lower()
            response = sanitize_input(response, "selection")

            if response in ['y', 'yes']:
                # Record this critical operation
                self.confirmation_history.append({
                    'timestamp': time.time(),
                    'operation': summary.operation_type,
                    'risk_level': summary.risk_level.value,
                    'paths_count': len(summary.target_paths),
                    'total_size': summary.total_size
                })
                return True
            elif response in ['n', 'no', '']:
                print("❌ Operation cancelled by user.")
                return False
            else:
                print("Please enter 'y' for yes or 'n' for no.")

    def _format_size(self, size_bytes: int) -> str:
        """Format size in human-readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB"

class PermissionChecker:
    """
    Permission validation system to ensure user has appropriate rights.
    """

    @staticmethod
    def check_write_permission(path: str) -> Tuple[bool, str]:
        """Check if user has write permission to path"""
        try:
            if not os.path.exists(path):
                # Check parent directory
                parent = os.path.dirname(path)
                if not os.path.exists(parent):
                    return False, f"Parent directory does not exist: {parent}"
                path = parent

            if os.access(path, os.W_OK):
                return True, "Write permission granted"
            else:
                return False, "Insufficient write permissions"

        except Exception as e:
            return False, f"Permission check failed: {str(e)}"

    @staticmethod
    def check_admin_required(paths: List[str]) -> bool:
        """Check if any paths require admin privileges"""
        admin_paths = [
            '/System',
            '/Library',
            '/usr',
            '/private/var'
        ]

        for path in paths:
            for admin_path in admin_paths:
                if path.startswith(admin_path):
                    return True
        return False

    @staticmethod
    def get_current_user_info() -> Dict[str, any]:
        """Get current user information"""
        import pwd
        import grp

        try:
            uid = os.getuid()
            gid = os.getgid()
            user_info = pwd.getpwuid(uid)
            group_info = grp.getgrgid(gid)

            return {
                'uid': uid,
                'gid': gid,
                'username': user_info.pw_name,
                'home_dir': user_info.pw_dir,
                'shell': user_info.pw_shell,
                'group_name': group_info.gr_name,
                'is_root': uid == 0
            }
        except Exception as e:
            return {'error': str(e)}

def determine_risk_level(paths: List[str], total_size: int, file_count: int) -> RiskLevel:
    """
    Determine risk level based on operation characteristics.

    Args:
        paths: List of paths to be affected
        total_size: Total size in bytes
        file_count: Number of files

    Returns:
        RiskLevel: Determined risk level
    """
    # Critical risk indicators
    critical_paths = ['/System', '/usr', '/bin', '/sbin', '/etc']
    if any(any(path.startswith(critical) for critical in critical_paths) for path in paths):
        return RiskLevel.CRITICAL

    # High risk thresholds
    if (total_size > 10 * 1024**3 or  # > 10GB
        file_count > 100000 or        # > 100k files
        len(paths) > 50):             # > 50 directories
        return RiskLevel.HIGH

    # Medium risk thresholds
    if (total_size > 1 * 1024**3 or   # > 1GB
        file_count > 10000 or         # > 10k files
        len(paths) > 10):             # > 10 directories
        return RiskLevel.MEDIUM

    # Default to low risk
    return RiskLevel.LOW

# Global confirmation dialog instance
confirmation_dialog = ConfirmationDialog()
permission_checker = PermissionChecker()

# Convenience functions
def get_confirmation(operation_type: str, paths: List[str], total_size: int,
                   file_count: int, warnings: List[str] = None) -> bool:
    """Get user confirmation for an operation"""
    risk_level = determine_risk_level(paths, total_size, file_count)

    summary = OperationSummary(
        operation_type=operation_type,
        target_paths=paths,
        total_size=total_size,
        file_count=file_count,
        risk_level=risk_level,
        warnings=warnings or [],
        estimated_time=max(1.0, file_count / 1000)  # Rough estimate
    )

    return confirmation_dialog.get_operation_confirmation(summary)

def check_permissions(paths: List[str]) -> Tuple[bool, List[str]]:
    """Check permissions for multiple paths"""
    failed_paths = []

    for path in paths:
        has_permission, reason = permission_checker.check_write_permission(path)
        if not has_permission:
            failed_paths.append(f"{path}: {reason}")

    return len(failed_paths) == 0, failed_paths