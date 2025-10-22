#!/usr/bin/env python3
"""
Audit and Logging System for LazyScan

This module provides comprehensive logging and audit trail functionality
to track all operations, security events, and user actions.

Author: Security Enhancement for LazyScan
Version: 1.0.0
"""

import getpass
import hashlib
import json
import logging
import logging.handlers
import os
import platform
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional


class EventType(Enum):
    """Types of events to log"""

    STARTUP = "startup"
    SHUTDOWN = "shutdown"
    SCAN_START = "scan_start"
    SCAN_COMPLETE = "scan_complete"
    DELETE_START = "delete_start"
    DELETE_COMPLETE = "delete_complete"
    DELETE_FAILED = "delete_failed"
    BACKUP_CREATED = "backup_created"
    BACKUP_FAILED = "backup_failed"
    SECURITY_VIOLATION = "security_violation"
    PERMISSION_DENIED = "permission_denied"
    USER_CONFIRMATION = "user_confirmation"
    USER_CANCELLATION = "user_cancellation"
    ERROR = "error"
    WARNING = "warning"
    CONFIG_CHANGE = "config_change"


class Severity(Enum):
    """Event severity levels"""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class AuditEvent:
    """Structured audit event"""

    timestamp: str
    event_type: EventType
    severity: Severity
    user: str
    session_id: str
    message: str
    details: dict[str, Any]
    system_info: dict[str, str]
    checksum: Optional[str] = None


class AuditLogger:
    """
    Comprehensive audit logging system with security features.
    """

    def __init__(self, log_dir: Optional[str] = None):
        # Setup log directory
        if log_dir:
            self.log_dir = Path(log_dir)
        else:
            self.log_dir = Path.home() / ".config" / "lazyscan" / "logs"

        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Generate session ID
        self.session_id = self._generate_session_id()

        # Setup logging files
        self.audit_log_file = self.log_dir / "audit.log"
        self.security_log_file = self.log_dir / "security.log"
        self.operation_log_file = self.log_dir / "operations.log"
        self.json_log_file = self.log_dir / "audit.jsonl"

        # Setup loggers
        self._setup_loggers()

        # System information
        self.system_info = self._get_system_info()

        # Log startup
        self.log_event(
            EventType.STARTUP,
            Severity.INFO,
            "LazyScan audit system initialized",
            {"version": "0.5.0", "session_id": self.session_id},
        )

    def _generate_session_id(self) -> str:
        """Generate unique session ID"""
        timestamp = str(int(time.time()))
        user = getpass.getuser()
        pid = str(os.getpid())

        session_data = f"{timestamp}-{user}-{pid}"
        return hashlib.md5(session_data.encode()).hexdigest()[:12]

    def _get_system_info(self) -> dict[str, str]:
        """Get system information for audit context"""
        return {
            "platform": platform.system(),
            "platform_version": platform.version(),
            "architecture": platform.architecture()[0],
            "hostname": platform.node(),
            "python_version": platform.python_version(),
            "user": getpass.getuser(),
            "pid": str(os.getpid()),
            "cwd": os.getcwd(),
        }

    def _setup_loggers(self) -> None:
        """Setup multiple specialized loggers"""
        # Main audit logger
        self.audit_logger = logging.getLogger("lazyscan.audit")
        self.audit_logger.setLevel(logging.DEBUG)

        # Security events logger
        self.security_logger = logging.getLogger("lazyscan.security")
        self.security_logger.setLevel(logging.INFO)

        # Operations logger
        self.operations_logger = logging.getLogger("lazyscan.operations")
        self.operations_logger.setLevel(logging.INFO)

        # Setup handlers with rotation
        self._setup_file_handlers()

        # Setup console handler for critical events
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.ERROR)
        console_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        console_handler.setFormatter(console_formatter)

        self.audit_logger.addHandler(console_handler)
        self.security_logger.addHandler(console_handler)

    def _setup_file_handlers(self) -> None:
        """Setup rotating file handlers"""
        # Audit log handler
        audit_handler = logging.handlers.RotatingFileHandler(
            self.audit_log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
        )
        audit_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        audit_handler.setFormatter(audit_formatter)
        self.audit_logger.addHandler(audit_handler)

        # Security log handler
        security_handler = logging.handlers.RotatingFileHandler(
            self.security_log_file,
            maxBytes=5 * 1024 * 1024,  # 5MB
            backupCount=10,
        )
        security_formatter = logging.Formatter(
            "%(asctime)s - SECURITY - %(levelname)s - %(message)s"
        )
        security_handler.setFormatter(security_formatter)
        self.security_logger.addHandler(security_handler)

        # Operations log handler
        operations_handler = logging.handlers.RotatingFileHandler(
            self.operation_log_file,
            maxBytes=20 * 1024 * 1024,  # 20MB
            backupCount=3,
        )
        operations_formatter = logging.Formatter("%(asctime)s - %(message)s")
        operations_handler.setFormatter(operations_formatter)
        self.operations_logger.addHandler(operations_handler)

    def log_event(
        self,
        event_type: EventType,
        severity: Severity,
        message: str,
        details: dict[str, Any] = None,
    ) -> None:
        """Log an audit event"""
        if details is None:
            details = {}

        # Create audit event
        event = AuditEvent(
            timestamp=datetime.now(timezone.utc).isoformat(),
            event_type=event_type,
            severity=severity,
            user=getpass.getuser(),
            session_id=self.session_id,
            message=message,
            details=details,
            system_info=self.system_info,
        )

        # Calculate checksum for integrity
        # Convert enum values to strings for JSON serialization
        event_dict = asdict(event)
        event_dict["event_type"] = event_dict["event_type"].value
        event_dict["severity"] = event_dict["severity"].value
        event_data = json.dumps(event_dict, sort_keys=True)
        event.checksum = hashlib.sha256(event_data.encode()).hexdigest()[:16]

        # Log to appropriate loggers
        log_level = self._severity_to_log_level(severity)

        # Main audit log
        self.audit_logger.log(
            log_level,
            f"[{event_type.value}] {message} | Details: {json.dumps(details)}",
        )

        # Security-specific events
        if event_type in [EventType.SECURITY_VIOLATION, EventType.PERMISSION_DENIED]:
            self.security_logger.log(
                log_level,
                f"[{event_type.value}] {message} | User: {event.user} | Details: {json.dumps(details)}",
            )

        # Operation-specific events
        if event_type in [
            EventType.SCAN_START,
            EventType.SCAN_COMPLETE,
            EventType.DELETE_START,
            EventType.DELETE_COMPLETE,
            EventType.DELETE_FAILED,
        ]:
            self.operations_logger.log(
                log_level,
                f"[{event_type.value}] {message} | Session: {self.session_id} | Details: {json.dumps(details)}",
            )

        # JSON structured log
        self._write_json_log(event)

    def _severity_to_log_level(self, severity: Severity) -> int:
        """Convert severity to logging level"""
        mapping = {
            Severity.DEBUG: logging.DEBUG,
            Severity.INFO: logging.INFO,
            Severity.WARNING: logging.WARNING,
            Severity.ERROR: logging.ERROR,
            Severity.CRITICAL: logging.CRITICAL,
        }
        return mapping.get(severity, logging.INFO)

    def _write_json_log(self, event: AuditEvent) -> None:
        """Write structured JSON log entry"""
        try:
            with open(self.json_log_file, "a") as f:
                # Convert enum values to strings for JSON serialization
                event_dict = asdict(event)
                event_dict["event_type"] = event_dict["event_type"].value
                event_dict["severity"] = event_dict["severity"].value
                json.dump(event_dict, f)
                f.write("\n")
        except Exception as e:
            self.audit_logger.error(f"Failed to write JSON log: {e}")

    def log_scan_operation(
        self, operation: str, paths: list[str], results: dict[str, Any]
    ) -> None:
        """Log scan operation with detailed results"""
        details = {
            "operation": operation,
            "paths_scanned": len(paths),
            "total_size_found": results.get("total_size", 0),
            "files_found": results.get("file_count", 0),
            "directories_found": results.get("dir_count", 0),
            "scan_duration": results.get("duration", 0),
            "paths": paths[:10],  # Limit to first 10 paths
        }

        self.log_event(
            EventType.SCAN_COMPLETE,
            Severity.INFO,
            f"Scan operation completed: {operation}",
            details,
        )

    def log_delete_operation(
        self, paths: list[str], success: bool, results: dict[str, Any]
    ) -> None:
        """Log deletion operation with results"""
        event_type = EventType.DELETE_COMPLETE if success else EventType.DELETE_FAILED
        severity = Severity.INFO if success else Severity.ERROR

        details = {
            "paths_targeted": len(paths),
            "success": success,
            "files_deleted": results.get("files_deleted", 0),
            "size_freed": results.get("size_freed", 0),
            "errors": results.get("errors", []),
            "duration": results.get("duration", 0),
            "paths": paths[:10],  # Limit to first 10 paths
        }

        message = (
            "Deletion operation completed successfully"
            if success
            else "Deletion operation failed"
        )

        self.log_event(event_type, severity, message, details)

    def log_security_event(
        self, event_description: str, violation_details: dict[str, Any]
    ) -> None:
        """Log security violation or concern"""
        details = {
            "violation_type": violation_details.get("type", "unknown"),
            "attempted_path": violation_details.get("path", ""),
            "reason": violation_details.get("reason", ""),
            "blocked": violation_details.get("blocked", True),
            "user_ip": violation_details.get("ip", "local"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        self.log_event(
            EventType.SECURITY_VIOLATION,
            Severity.WARNING,
            f"Security event: {event_description}",
            details,
        )

    def log_user_action(
        self, action: str, confirmed: bool, context: dict[str, Any]
    ) -> None:
        """Log user confirmation or cancellation"""
        event_type = (
            EventType.USER_CONFIRMATION if confirmed else EventType.USER_CANCELLATION
        )

        details = {
            "action": action,
            "confirmed": confirmed,
            "risk_level": context.get("risk_level", "unknown"),
            "paths_count": context.get("paths_count", 0),
            "total_size": context.get("total_size", 0),
            "confirmation_method": context.get("confirmation_method", "standard"),
        }

        message = f"User {'confirmed' if confirmed else 'cancelled'} action: {action}"

        self.log_event(event_type, Severity.INFO, message, details)

    def log_backup_operation(
        self,
        source_path: str,
        backup_path: str,
        success: bool,
        details: dict[str, Any] = None,
    ) -> None:
        """Log backup operation"""
        event_type = EventType.BACKUP_CREATED if success else EventType.BACKUP_FAILED
        severity = Severity.INFO if success else Severity.ERROR

        log_details = {
            "source_path": source_path,
            "backup_path": backup_path if success else "failed",
            "success": success,
            "size": details.get("size", 0) if details else 0,
            "duration": details.get("duration", 0) if details else 0,
            "error": details.get("error", "") if details else "",
        }

        message = f"Backup {'created' if success else 'failed'}: {source_path}"

        self.log_event(event_type, severity, message, log_details)

    def get_audit_summary(self, hours: int = 24) -> dict[str, Any]:
        """Get audit summary for the last N hours"""
        cutoff_time = time.time() - (hours * 3600)

        summary = {
            "period_hours": hours,
            "session_id": self.session_id,
            "events_by_type": {},
            "events_by_severity": {},
            "security_events": 0,
            "operations_completed": 0,
            "operations_failed": 0,
            "total_events": 0,
        }

        try:
            # Read JSON log file
            if self.json_log_file.exists():
                with open(self.json_log_file) as f:
                    for line in f:
                        try:
                            event_data = json.loads(line.strip())
                            event_time = datetime.fromisoformat(
                                event_data["timestamp"].replace("Z", "+00:00")
                            ).timestamp()

                            if event_time >= cutoff_time:
                                summary["total_events"] += 1

                                # Count by type
                                event_type = event_data["event_type"]
                                summary["events_by_type"][event_type] = (
                                    summary["events_by_type"].get(event_type, 0) + 1
                                )

                                # Count by severity
                                severity = event_data["severity"]
                                summary["events_by_severity"][severity] = (
                                    summary["events_by_severity"].get(severity, 0) + 1
                                )

                                # Special counters
                                if event_type == "security_violation":
                                    summary["security_events"] += 1
                                elif event_type in ["scan_complete", "delete_complete"]:
                                    summary["operations_completed"] += 1
                                elif event_type in ["delete_failed", "backup_failed"]:
                                    summary["operations_failed"] += 1

                        except json.JSONDecodeError:
                            continue

        except Exception as e:
            self.audit_logger.error(f"Failed to generate audit summary: {e}")

        return summary

    def export_audit_logs(self, output_file: str, hours: int = 24) -> bool:
        """Export audit logs to file"""
        try:
            cutoff_time = time.time() - (hours * 3600)
            events = []

            if self.json_log_file.exists():
                with open(self.json_log_file) as f:
                    for line in f:
                        try:
                            event_data = json.loads(line.strip())
                            event_time = datetime.fromisoformat(
                                event_data["timestamp"].replace("Z", "+00:00")
                            ).timestamp()

                            if event_time >= cutoff_time:
                                events.append(event_data)
                        except json.JSONDecodeError:
                            continue

            # Write export file
            export_data = {
                "export_timestamp": datetime.now(timezone.utc).isoformat(),
                "period_hours": hours,
                "total_events": len(events),
                "events": events,
            }

            with open(output_file, "w") as f:
                json.dump(export_data, f, indent=2)

            self.log_event(
                EventType.CONFIG_CHANGE,
                Severity.INFO,
                f"Audit logs exported to {output_file}",
                {"events_exported": len(events), "period_hours": hours},
            )

            return True

        except Exception as e:
            self.log_event(
                EventType.ERROR,
                Severity.ERROR,
                f"Failed to export audit logs: {e!s}",
                {"output_file": output_file},
            )
            return False

    def cleanup_old_logs(self, days_to_keep: int = 30) -> None:
        """Clean up old log files"""
        try:
            cutoff_time = time.time() - (days_to_keep * 24 * 3600)

            # Clean up rotated log files
            for log_file in self.log_dir.glob("*.log.*"):
                if log_file.stat().st_mtime < cutoff_time:
                    log_file.unlink()
                    self.audit_logger.info(f"Cleaned up old log file: {log_file}")

            # Clean up old JSON log entries
            if self.json_log_file.exists():
                temp_file = self.json_log_file.with_suffix(".tmp")

                with (
                    open(self.json_log_file) as infile,
                    open(temp_file, "w") as outfile,
                ):
                    for line in infile:
                        try:
                            event_data = json.loads(line.strip())
                            event_time = datetime.fromisoformat(
                                event_data["timestamp"].replace("Z", "+00:00")
                            ).timestamp()

                            if event_time >= cutoff_time:
                                outfile.write(line)
                        except json.JSONDecodeError:
                            continue

                temp_file.replace(self.json_log_file)

            self.log_event(
                EventType.CONFIG_CHANGE,
                Severity.INFO,
                f"Cleaned up logs older than {days_to_keep} days",
                {"days_to_keep": days_to_keep},
            )

        except Exception as e:
            self.log_event(
                EventType.ERROR,
                Severity.ERROR,
                f"Failed to cleanup old logs: {e!s}",
                {"days_to_keep": days_to_keep},
            )

    def log_startup(self, details: dict[str, Any] = None) -> None:
        """Log application startup"""
        self.log_event(
            EventType.STARTUP,
            Severity.INFO,
            "LazyScan application started",
            details or {},
        )

    def log_shutdown(self, details: dict[str, Any] = None) -> None:
        """Log application shutdown"""
        self.log_event(
            EventType.SHUTDOWN,
            Severity.INFO,
            "LazyScan application shutting down",
            details or {},
        )

    def shutdown(self) -> None:
        """Shutdown audit system"""
        self.log_event(
            EventType.SHUTDOWN,
            Severity.INFO,
            "LazyScan audit system shutting down",
            {"session_duration": time.time() - int(self.session_id[-8:], 16)},
        )

        # Close all handlers
        for handler in self.audit_logger.handlers[:]:
            handler.close()
            self.audit_logger.removeHandler(handler)

        for handler in self.security_logger.handlers[:]:
            handler.close()
            self.security_logger.removeHandler(handler)

        for handler in self.operations_logger.handlers[:]:
            handler.close()
            self.operations_logger.removeHandler(handler)


# Global audit logger instance
audit_logger = AuditLogger()


# Convenience functions
def log_scan(operation: str, paths: list[str], results: dict[str, Any]) -> None:
    """Log scan operation"""
    audit_logger.log_scan_operation(operation, paths, results)


def log_delete(paths: list[str], success: bool, results: dict[str, Any]) -> None:
    """Log deletion operation"""
    audit_logger.log_delete_operation(paths, success, results)


def log_security_violation(description: str, details: dict[str, Any]) -> None:
    """Log security violation"""
    audit_logger.log_security_event(description, details)


def log_user_confirmation(
    action: str, confirmed: bool, context: dict[str, Any]
) -> None:
    """Log user confirmation/cancellation"""
    audit_logger.log_user_action(action, confirmed, context)


def log_backup(
    source: str, backup: str, success: bool, details: dict[str, Any] = None
) -> None:
    """Log backup operation"""
    audit_logger.log_backup_operation(source, backup, success, details)


def get_audit_summary(hours: int = 24) -> dict[str, Any]:
    """Get audit summary"""
    return audit_logger.get_audit_summary(hours)
