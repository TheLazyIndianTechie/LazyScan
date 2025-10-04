#!/usr/bin/env python3
"""
Structured logging framework for LazyScan.

Provides:
- JSON structured logging for audit trails and machine parsing
- Human-readable console logging with optional colors
- Context management for operation tracking
- Console adapter functions to replace print statements
- Integration with error handling system
"""

import logging
import logging.handlers
import json
import sys
import threading
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from pathlib import Path
from enum import Enum
from contextlib import contextmanager


class LogLevel(Enum):
    """Structured log levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogFormat(Enum):
    """Supported log output formats."""

    JSON = "json"
    HUMAN = "human"


# Thread-local storage for log context
_context_storage = threading.local()


def generate_correlation_id() -> str:
    """Generate a unique correlation ID for operation tracking."""
    import uuid
    return str(uuid.uuid4())[:8]


def get_current_correlation_id() -> Optional[str]:
    """Get the current correlation ID from context."""
    context = getattr(_context_storage, "context", {})
    return context.get("correlation_id")


class ContextualFormatter(logging.Formatter):
    """Base formatter that includes contextual information."""

    def __init__(self, include_context: bool = True):
        super().__init__()
        self.include_context = include_context

    def format(self, record: logging.LogRecord) -> str:
        # Add contextual information to the record
        if self.include_context:
            context = getattr(_context_storage, "context", {})
            for key, value in context.items():
                if not hasattr(record, key):
                    setattr(record, key, value)

        return super().format(record)


class JSONFormatter(ContextualFormatter):
    """JSON structured logging formatter."""

    def format(self, record: logging.LogRecord) -> str:
        # Build base log entry
        log_entry = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add exception information if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Add any additional context from the record
        context = getattr(_context_storage, "context", {})
        for key, value in context.items():
            if key not in log_entry:
                log_entry[key] = value

        # Add custom attributes from the record
        for key, value in record.__dict__.items():
            if key not in [
                "name",
                "msg",
                "args",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
                "message",
                "exc_info",
                "exc_text",
                "stack_info",
            ]:
                log_entry[key] = value

        return json.dumps(log_entry, default=str, ensure_ascii=False)


class HumanFormatter(ContextualFormatter):
    """Human-readable console logging formatter."""

    def __init__(self, enable_colors: bool = True, include_context: bool = True):
        super().__init__(include_context)
        self.enable_colors = enable_colors and sys.stderr.isatty()

        # ANSI color codes
        self.colors = (
            {
                "DEBUG": "\033[90m",  # Dark gray
                "INFO": "\033[36m",  # Cyan
                "WARNING": "\033[33m",  # Yellow
                "ERROR": "\033[31m",  # Red
                "CRITICAL": "\033[35m",  # Magenta
                "RESET": "\033[0m",  # Reset
            }
            if self.enable_colors
            else {}
        )

    def format(self, record: logging.LogRecord) -> str:
        # Filter out console print statements - they should not be displayed as log messages
        if hasattr(record, 'print_statement') and record.print_statement:
            # Return just the message without any log formatting
            return record.getMessage()

        # Add contextual information to the record first
        if self.include_context:
            context = getattr(_context_storage, "context", {})
            for key, value in context.items():
                if not hasattr(record, key):
                    setattr(record, key, value)

        # Format timestamp
        timestamp = datetime.fromtimestamp(record.created).strftime("%H:%M:%S")

        # Add color if enabled
        level_color = self.colors.get(record.levelname, "")
        reset_color = self.colors.get("RESET", "")

        # Format level indicator with emoji
        level_indicators = {
            "DEBUG": "🔍",
            "INFO": "ℹ️",
            "WARNING": "⚠️",
            "ERROR": "❌",
            "CRITICAL": "🚨",
        }

        level_indicator = level_indicators.get(record.levelname, "•")

        # Build the main message
        message = record.getMessage()

        # Format the log line
        log_line = f"{level_color}{timestamp} {level_indicator} {message}{reset_color}"

        # Add context information if present and relevant
        context_parts = []

        # Add operation context if present
        if hasattr(record, "operation"):
            context_parts.append(f"op={record.operation}")

        # Add path context if present
        if hasattr(record, "path"):
            context_parts.append(f"path={record.path}")

        # Add other relevant context
        for key in ["app_type", "policy_hash", "context_id"]:
            if hasattr(record, key):
                context_parts.append(f"{key}={getattr(record, key)}")

        if context_parts:
            context_str = " • " + " • ".join(context_parts)
            log_line += (
                f"\033[90m{context_str}\033[0m" if self.enable_colors else context_str
            )

        # Add exception information if present
        if record.exc_info:
            exc_str = self.formatException(record.exc_info)
            log_line += f"\n{exc_str}"

        return log_line


class StructuredLogger:
    """Enhanced logger with context management."""

    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.name = name

    def debug(self, message: str, **context):
        """Log debug message with optional context."""
        self._log(logging.DEBUG, message, context)

    def info(self, message: str, **context):
        """Log info message with optional context."""
        self._log(logging.INFO, message, context)

    def warning(self, message: str, **context):
        """Log warning message with optional context."""
        self._log(logging.WARNING, message, context)

    def error(self, message: str, **context):
        """Log error message with optional context."""
        self._log(logging.ERROR, message, context)

    def critical(self, message: str, **context):
        """Log critical message with optional context."""
        self._log(logging.CRITICAL, message, context)

    def _log(self, level: int, message: str, context: Dict[str, Any]):
        """Internal logging method that adds context to the record."""
        if self.logger.isEnabledFor(level):
            # Create record with extra context
            record = self.logger.makeRecord(
                self.logger.name, level, "(no file)", 0, message, (), None
            )

            # Add context as record attributes
            for key, value in context.items():
                setattr(record, key, value)

            self.logger.handle(record)


def setup_logging(
    console_format: str = "human",
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    enable_colors: bool = True,
    max_file_size: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
) -> None:
    """
    Configure the logging system.

    Args:
        console_format: 'json' or 'human' format for console output
        log_level: Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file path for log output
        enable_colors: Whether to use colors in human format (ignored in json format)
        max_file_size: Maximum size for log files before rotation
        backup_count: Number of backup log files to keep
    """

    # Clear any existing handlers
    root_logger = logging.getLogger()
    root_logger.handlers.clear()

    # Set log level
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    root_logger.setLevel(numeric_level)

    # Setup console handler
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(numeric_level)

    if console_format.lower() == "json":
        console_formatter = JSONFormatter()
    else:
        console_formatter = HumanFormatter(enable_colors=enable_colors)

    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # Setup file handler if specified
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=max_file_size, backupCount=backup_count, encoding="utf-8"
        )
        file_handler.setLevel(numeric_level)

        # Always use JSON format for file output
        file_formatter = JSONFormatter()
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)

    # Prevent duplicate logging
    root_logger.propagate = False


def get_logger(name: str) -> StructuredLogger:
    """
    Get a structured logger instance.

    Args:
        name: Logger name (typically __name__)

    Returns:
        StructuredLogger instance
    """
    return StructuredLogger(name)


@contextmanager
def log_context(**context):
    """
    Context manager for adding contextual information to logs.

    Usage:
        with log_context(operation="file_scan", app_type="unity"):
            logger.info("Starting scan")  # Will include operation and app_type
    """
    # Get existing context or create new
    existing_context = getattr(_context_storage, "context", {})

    # Merge with new context
    new_context = {**existing_context, **context}
    _context_storage.context = new_context

    try:
        yield
    finally:
        # Restore previous context
        _context_storage.context = existing_context


@contextmanager
def log_operation(operation_name: str, **context):
    """
    Context manager for logging operation lifecycle with automatic timing and correlation.

    Usage:
        with log_operation("file_scan", scan_path="/tmp"):
            # Do work
            pass
        # Automatically logs start, completion/failure with timing
    """
    correlation_id = generate_correlation_id()
    start_time = datetime.now(timezone.utc)

    # Add correlation ID to context
    operation_context = {
        "correlation_id": correlation_id,
        "operation": operation_name,
        **context
    }

    with log_context(**operation_context):
        try:
            log_operation_start(operation_name, **context)
            yield correlation_id
        except Exception as e:
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            log_operation_failed(
                operation_name,
                str(e),
                duration_seconds=duration,
                correlation_id=correlation_id,
                **context
            )
            raise
        else:
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            log_operation_complete(
                operation_name,
                duration=duration,
                correlation_id=correlation_id,
                **context
            )


class ConsoleAdapter:
    """
    Console adapter to replace print statements with structured logging.

    Provides drop-in replacements for print functions that route through
    the logging system while maintaining user-friendly console output.
    """

    def __init__(self, logger_name: str = "console"):
        self.logger = get_logger(logger_name)

    def print(self, *args, **kwargs):
        """Drop-in replacement for print() that uses logging."""
        # Handle print arguments similar to built-in print
        sep = kwargs.get("sep", " ")
        message = sep.join(str(arg) for arg in args)

        # Use info level for normal print statements
        self.logger.info(message, print_statement=True)

    def print_error(self, *args, **kwargs):
        """Print error messages (replacement for print to stderr)."""
        sep = kwargs.get("sep", " ")
        message = sep.join(str(arg) for arg in args)

        self.logger.error(message, print_statement=True)

    def print_warning(self, *args, **kwargs):
        """Print warning messages."""
        sep = kwargs.get("sep", " ")
        message = sep.join(str(arg) for arg in args)

        self.logger.warning(message, print_statement=True)

    def print_debug(self, *args, **kwargs):
        """Print debug messages."""
        sep = kwargs.get("sep", " ")
        message = sep.join(str(arg) for arg in args)

        self.logger.debug(message, print_statement=True)

    def print_success(self, *args, **kwargs):
        """Print success messages with green color."""
        sep = kwargs.get("sep", " ")
        message = sep.join(str(arg) for arg in args)

        self.logger.info(f"✅ {message}", print_statement=True, message_type="success")

    def print_info(self, *args, **kwargs):
        """Print informational messages."""
        sep = kwargs.get("sep", " ")
        message = sep.join(str(arg) for arg in args)

        self.logger.info(f"ℹ️ {message}", print_statement=True, message_type="info")


# Global console adapter instance
_console_adapter = None


def get_console() -> ConsoleAdapter:
    """Get the global console adapter instance."""
    global _console_adapter
    if _console_adapter is None:
        _console_adapter = ConsoleAdapter()
    return _console_adapter


def configure_logging(level: str = "INFO", format_type: str = "human") -> None:
    """
    Configure the root logger with specified level and format.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_type: Format type - "human" or "json"
    """
    import logging

    # Convert string level to logging constant
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    # Configure root logger
    if format_type == "human":
        logging.basicConfig(
            level=numeric_level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            force=True,  # Override any existing configuration
        )
    else:
        # For JSON format, we'll use our custom formatter
        logging.basicConfig(
            level=numeric_level,
            force=True,  # Override any existing configuration
        )

    # Set level for our specific loggers
    lazyscan_logger = logging.getLogger("lazyscan")
    lazyscan_logger.setLevel(numeric_level)


def configure_audit_logging(
    audit_file: str, audit_level: str = "INFO", include_security_events: bool = True
) -> None:
    """
    Configure dedicated audit logging for security and compliance.

    Args:
        audit_file: Path to audit log file
        audit_level: Minimum level for audit events
        include_security_events: Whether to include security-specific events
    """

    audit_logger = logging.getLogger("lazyscan.audit")

    # Remove existing handlers
    audit_logger.handlers.clear()

    # Setup rotating file handler for audit logs
    audit_path = Path(audit_file)
    audit_path.parent.mkdir(parents=True, exist_ok=True)

    audit_handler = logging.handlers.RotatingFileHandler(
        audit_file, maxBytes=50 * 1024 * 1024, backupCount=10, encoding="utf-8"  # 50MB
    )

    # Set audit log level
    numeric_level = getattr(logging, audit_level.upper(), logging.INFO)
    audit_handler.setLevel(numeric_level)
    audit_logger.setLevel(numeric_level)

    # Always use JSON format for audit logs
    audit_formatter = JSONFormatter()
    audit_handler.setFormatter(audit_formatter)

    audit_logger.addHandler(audit_handler)
    audit_logger.propagate = False  # Don't send to root logger


def get_audit_logger() -> StructuredLogger:
    """Get the dedicated audit logger."""
    return StructuredLogger("lazyscan.audit")


class PerformanceProfiler:
    """Simple performance profiling integrated with logging."""

    def __init__(self, logger: StructuredLogger, operation: str):
        self.logger = logger
        self.operation = operation
        self.start_time = None

    def __enter__(self):
        """Start timing the operation."""
        self.start_time = datetime.now(timezone.utc)
        self.logger.debug(
            f"Starting {self.operation}",
            operation=self.operation,
            event_type="operation_start",
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Log operation completion with timing."""
        if self.start_time:
            duration = (datetime.now(timezone.utc) - self.start_time).total_seconds()

            if exc_type:
                self.logger.error(
                    f"{self.operation} failed after {duration:.3f}s",
                    operation=self.operation,
                    duration_seconds=duration,
                    event_type="operation_failed",
                    exception_type=exc_type.__name__ if exc_type else None,
                )
            else:
                self.logger.info(
                    f"{self.operation} completed in {duration:.3f}s",
                    operation=self.operation,
                    duration_seconds=duration,
                    event_type="operation_completed",
                )


def profile_operation(logger: StructuredLogger, operation: str) -> PerformanceProfiler:
    """Create a performance profiler for an operation."""
    return PerformanceProfiler(logger, operation)


# Security event logging utilities
def log_security_event(
    event_type: str, severity: str, description: str, **context
) -> None:
    """
    Log security-related events to audit trail.

    Args:
        event_type: Type of security event (e.g., 'deletion_blocked', 'policy_violation')
        severity: Event severity ('info', 'warning', 'error', 'critical')
        description: Human-readable description of the event
        **context: Additional context for the event
    """
    audit_logger = get_audit_logger()

    # Filter out any keys that might conflict with StructuredLogger method parameters
    filtered_context = {k: v for k, v in context.items() if k not in ["message"]}

    log_context_data = {
        "event_type": event_type,
        "security_event": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **filtered_context,
    }

    severity_level = severity.upper()
    if severity_level == "INFO":
        audit_logger.info(description, **log_context_data)
    elif severity_level == "WARNING":
        audit_logger.warning(description, **log_context_data)
    elif severity_level == "ERROR":
        audit_logger.error(description, **log_context_data)
    elif severity_level == "CRITICAL":
        audit_logger.critical(description, **log_context_data)
    else:
        audit_logger.info(description, **log_context_data)


def log_deletion_event(path: str, deletion_mode: str, result: str, **context) -> None:
    """Log file deletion events for audit purposes."""
    log_security_event(
        event_type="file_deletion",
        severity="info" if result == "success" else "warning",
        description=f"File deletion {result}: {path}",
        path=path,
        deletion_mode=deletion_mode,
        deletion_result=result,
        **context,
    )


def log_policy_enforcement(
    action: str, result: str, policy_hash: str, **context
) -> None:
    """Log security policy enforcement events."""
    severity = "error" if result == "denied" else "info"

    log_security_event(
        event_type="policy_enforcement",
        severity=severity,
        description=f"Policy enforcement: {action} {result}",
        action=action,
        enforcement_result=result,
        policy_hash=policy_hash,
        **context,
    )


def log_recovery_operation(
    operation_type: str, operation_id: str, success: bool, **context
) -> None:
    """Log recovery operation events."""
    severity = "error" if not success else "info"

    log_security_event(
        event_type="recovery_operation",
        severity=severity,
        description=f"Recovery operation {'succeeded' if success else 'failed'}: {operation_type}",
        operation_type=operation_type,
        operation_id=operation_id,
        recovery_success=success,
        **context,
    )


def log_cleanup_operation(
    app_name: str, files_cleaned: int, size_cleaned: int, **context
) -> None:
    """Log cache cleanup operation events."""
    log_security_event(
        event_type="cleanup_operation",
        severity="info",
        description=f"Cache cleanup completed: {app_name}",
        app_name=app_name,
        files_cleaned=files_cleaned,
        size_cleaned=size_cleaned,
        **context,
    )


def log_scan_operation(
    scan_path: str, files_found: int, total_size: int, **context
) -> None:
    """Log directory scan operation events."""
    log_security_event(
        event_type="scan_operation",
        severity="info",
        description=f"Directory scan completed: {scan_path}",
        scan_path=scan_path,
        files_found=files_found,
        total_size=total_size,
        **context,
    )


def log_operation_start(operation_name: str, **context) -> None:
    """Log the start of an operation."""
    log_security_event(
        event_type="operation_start",
        severity="info",
        description=f"Operation started: {operation_name}",
        operation_name=operation_name,
        **context,
    )


def log_operation_complete(operation_name: str, duration: Optional[float] = None, **context) -> None:
    """Log the completion of an operation."""
    description = f"Operation completed: {operation_name}"
    if duration is not None:
        description += f" in {duration:.3f}s"

    log_security_event(
        event_type="operation_complete",
        severity="info",
        description=description,
        operation_name=operation_name,
        duration_seconds=duration,
        **context,
    )


def log_operation_failed(operation_name: str, error: str, **context) -> None:
    """Log the failure of an operation."""
    log_security_event(
        event_type="operation_failed",
        severity="error",
        description=f"Operation failed: {operation_name} - {error}",
        operation_name=operation_name,
        error_message=error,
        **context,
    )


def log_performance_metric(operation: str, metric_name: str, value: float, **context) -> None:
    """Log performance metrics."""
    log_security_event(
        event_type="performance_metric",
        severity="info",
        description=f"Performance metric: {operation}.{metric_name} = {value}",
        operation=operation,
        metric_name=metric_name,
        metric_value=value,
        **context,
    )


def log_cache_operation(
    cache_type: str, action: str, items_affected: int, size_affected: int, **context
) -> None:
    """Log cache-related operations."""
    severity = "warning" if action in ["delete", "clean"] else "info"

    log_security_event(
        event_type="cache_operation",
        severity=severity,
        description=f"Cache {action}: {cache_type} ({items_affected} items, {size_affected} bytes)",
        cache_type=cache_type,
        action=action,
        items_affected=items_affected,
        size_affected=size_affected,
        **context,
    )


def log_user_interaction(action: str, **context) -> None:
    """Log user interactions for audit purposes."""
    log_security_event(
        event_type="user_interaction",
        severity="info",
        description=f"User interaction: {action}",
        action=action,
        **context,
    )


# Convenience functions for common logging patterns
def setup_production_logging(
    app_name: str = "lazyscan", log_dir: str = "./logs", enable_audit: bool = True
) -> None:
    """
    Setup production-ready logging configuration.

    Args:
        app_name: Application name for log files
        log_dir: Directory for log files
        enable_audit: Whether to enable dedicated audit logging
    """
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # Main application logs
    main_log_file = log_path / f"{app_name}.log"
    setup_logging(
        console_format="human",
        log_level="INFO",
        log_file=str(main_log_file),
        enable_colors=True,
    )

    # Audit logs if enabled
    if enable_audit:
        audit_log_file = log_path / f"{app_name}_audit.log"
        configure_audit_logging(audit_file=str(audit_log_file), audit_level="INFO")


def setup_development_logging(verbose: bool = False) -> None:
    """
    Setup development-friendly logging configuration.

    Args:
        verbose: Enable debug level logging
    """
    level = "DEBUG" if verbose else "INFO"

    setup_logging(console_format="human", log_level=level, enable_colors=True)


def setup_ci_logging() -> None:
    """Setup logging for CI/CD environments."""
    setup_logging(console_format="json", log_level="INFO", enable_colors=False)


# Export commonly used functions
__all__ = [
    "LogLevel",
    "LogFormat",
    "setup_logging",
    "get_logger",
    "get_console",
    "log_context",
    "profile_operation",
    "log_security_event",
    "log_deletion_event",
    "log_policy_enforcement",
    "configure_audit_logging",
    "get_audit_logger",
    "setup_production_logging",
    "setup_development_logging",
    "setup_ci_logging",
    "ConsoleAdapter",
    "StructuredLogger",
]
