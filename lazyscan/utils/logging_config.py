#!/usr/bin/env python3
"""
Structured logging configuration for LazyScan.
Provides configurable, structured logging to replace print statements.
"""

import logging
import logging.config
import json
import sys
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Union
from pathlib import Path


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured JSON logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON."""
        
        # Base structured data
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add extra fields if present
        if hasattr(record, 'path'):
            log_data['path'] = record.path
        if hasattr(record, 'context'):
            log_data['context'] = record.context
        if hasattr(record, 'operation'):
            log_data['operation'] = record.operation
        if hasattr(record, 'size_mb'):
            log_data['size_mb'] = record.size_mb
        if hasattr(record, 'dry_run'):
            log_data['dry_run'] = record.dry_run
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        # Add any other extra fields
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                          'filename', 'module', 'exc_info', 'exc_text', 'stack_info',
                          'lineno', 'funcName', 'created', 'msecs', 'relativeCreated',
                          'thread', 'threadName', 'processName', 'process', 'getMessage',
                          'message']:
                if not key.startswith('_'):
                    log_data['extra_' + key] = value
        
        return json.dumps(log_data, default=str)


class ConsoleFormatter(logging.Formatter):
    """Custom formatter for human-readable console output."""
    
    def __init__(self, use_colors: bool = None):
        super().__init__()
        self.use_colors = use_colors
        if use_colors is None:
            self.use_colors = sys.stderr.isatty()
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record for console output."""
        
        # Color codes
        colors = {
            'DEBUG': '\033[36m',    # Cyan
            'INFO': '\033[32m',     # Green  
            'WARNING': '\033[33m',  # Yellow
            'ERROR': '\033[31m',    # Red
            'CRITICAL': '\033[35m', # Magenta
            'RESET': '\033[0m'      # Reset
        } if self.use_colors else {k: '' for k in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL', 'RESET']}
        
        # Format timestamp
        timestamp = datetime.fromtimestamp(record.created).strftime('%H:%M:%S')
        
        # Format base message
        level_color = colors.get(record.levelname, '')
        reset_color = colors['RESET']
        
        base_msg = (
            f"{timestamp} "
            f"{level_color}[{record.levelname:8}]{reset_color} "
            f"{record.name}: {record.getMessage()}"
        )
        
        # Add extra context if available
        extras = []
        if hasattr(record, 'path'):
            extras.append(f"path={record.path}")
        if hasattr(record, 'context'):
            extras.append(f"context={record.context}")
        if hasattr(record, 'operation'):
            extras.append(f"operation={record.operation}")
        if hasattr(record, 'dry_run'):
            extras.append(f"dry_run={record.dry_run}")
        
        if extras:
            base_msg += f" ({', '.join(extras)})"
        
        # Add exception info if present
        if record.exc_info:
            base_msg += "\n" + self.formatException(record.exc_info)
        
        return base_msg


def configure_logging(
    level: Union[str, int] = "INFO",
    format_type: str = "console", 
    log_file: Optional[Path] = None,
    use_colors: bool = None
) -> None:
    """
    Configure the logging system for LazyScan.
    
    Args:
        level: Logging level ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
        format_type: Format type ('console' or 'json')
        log_file: Optional file to log to (in addition to console)
        use_colors: Whether to use colors in console output (auto-detected if None)
    """
    
    # Convert string level to numeric
    if isinstance(level, str):
        numeric_level = getattr(logging, level.upper())
    else:
        numeric_level = level
    
    # Set root logger level
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Clear any existing handlers
    root_logger.handlers.clear()
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(numeric_level)
    
    # Set formatter based on format type
    if format_type == "json":
        console_formatter = StructuredFormatter()
    else:
        console_formatter = ConsoleFormatter(use_colors=use_colors)
    
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # Create file handler if log file is specified
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(numeric_level)
        
        # Always use JSON format for file logging
        file_formatter = StructuredFormatter()
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
    
    # Set levels for noisy third-party loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    
    # Log configuration
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured: level={logging.getLevelName(numeric_level)}, "
               f"format={format_type}, file={'yes' if log_file else 'no'}")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for the given name.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        logging.Logger: Configured logger instance
    """
    return logging.getLogger(name)


class LogContext:
    """Context manager for adding structured context to log messages."""
    
    def __init__(self, logger: logging.Logger, **context):
        """
        Initialize log context.
        
        Args:
            logger: Logger to add context to
            **context: Context key-value pairs to add to log messages
        """
        self.logger = logger
        self.context = context
        self.old_log_methods = {}
    
    def __enter__(self):
        """Enter context manager and patch logger methods."""
        # Store original methods
        self.old_log_methods = {
            'debug': self.logger.debug,
            'info': self.logger.info, 
            'warning': self.logger.warning,
            'error': self.logger.error,
            'critical': self.logger.critical
        }
        
        # Patch methods to include context
        for level_name, original_method in self.old_log_methods.items():
            def make_contextual_method(original):
                def contextual_method(msg, *args, **kwargs):
                    # Merge context into extra field
                    extra = kwargs.get('extra', {})
                    extra.update(self.context)
                    kwargs['extra'] = extra
                    return original(msg, *args, **kwargs)
                return contextual_method
            
            setattr(self.logger, level_name, make_contextual_method(original_method))
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager and restore original logger methods."""
        # Restore original methods
        for level_name, original_method in self.old_log_methods.items():
            setattr(self.logger, level_name, original_method)


def log_with_context(logger: logging.Logger, **context):
    """
    Create a context manager for adding structured context to log messages.
    
    Args:
        logger: Logger to add context to
        **context: Context key-value pairs
        
    Returns:
        LogContext: Context manager
        
    Example:
        with log_with_context(logger, operation="delete", path="/tmp/test"):
            logger.info("Starting operation")  # Will include operation and path
    """
    return LogContext(logger, **context)


# Console adapter for maintaining UX while using logging backend
class ConsoleAdapter:
    """Adapter to provide console-like interface while using structured logging."""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
    
    def print_info(self, message: str, **context):
        """Print informational message."""
        self.logger.info(message, extra=context)
    
    def print_warning(self, message: str, **context):
        """Print warning message."""
        self.logger.warning(message, extra=context)
    
    def print_error(self, message: str, **context):
        """Print error message."""
        self.logger.error(message, extra=context)
    
    def print_success(self, message: str, **context):
        """Print success message."""
        self.logger.info(f"✅ {message}", extra=context)
    
    def print_debug(self, message: str, **context):
        """Print debug message."""
        self.logger.debug(message, extra=context)


def get_console_adapter(logger_name: str) -> ConsoleAdapter:
    """
    Get a console adapter for the given logger name.
    
    Args:
        logger_name: Name of the logger
        
    Returns:
        ConsoleAdapter: Console adapter instance
    """
    logger = get_logger(logger_name)
    return ConsoleAdapter(logger)


# Default configuration
_default_configured = False

def ensure_default_logging():
    """Ensure logging is configured with sensible defaults."""
    global _default_configured
    
    if not _default_configured:
        configure_logging(level="INFO", format_type="console")
        _default_configured = True


# Auto-configure on import
ensure_default_logging()
