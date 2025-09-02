#!/usr/bin/env python3
"""
Custom exception hierarchy for LazyScan.
Provides typed exceptions to replace generic exception handling and enable
structured error reporting with proper exit codes.
"""

import sys
import traceback
from typing import Optional, Dict, Any, List
from enum import IntEnum


class ExitCode(IntEnum):
    """Standard exit codes for LazyScan operations."""
    SUCCESS = 0
    GENERAL_ERROR = 1
    MISUSE_OF_CLI = 2
    PATH_ERROR = 3
    PERMISSION_ERROR = 4
    SECURITY_ERROR = 5
    CONFIG_ERROR = 6
    USER_CANCELLED = 7
    PLATFORM_ERROR = 8
    DISCOVERY_ERROR = 9
    VALIDATION_ERROR = 10
    DELETION_ERROR = 11
    NETWORK_ERROR = 12
    DEPENDENCY_ERROR = 13


class LazyScanError(Exception):
    """Base exception for all LazyScan errors.
    
    Attributes:
        exit_code: Suggested exit code for CLI
        context: Additional context for logging and debugging
        user_message: Human-friendly error message
    """
    
    def __init__(self, message: str, exit_code: int = ExitCode.GENERAL_ERROR, 
                 context: Optional[Dict[str, Any]] = None, 
                 user_message: Optional[str] = None):
        super().__init__(message)
        self.exit_code = exit_code
        self.context = context or {}
        self.user_message = user_message or message
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for structured logging."""
        return {
            'exception_type': self.__class__.__name__,
            'message': str(self),
            'user_message': self.user_message,
            'exit_code': self.exit_code,
            'context': self.context
        }


class PathValidationError(LazyScanError):
    """Raised when path validation fails."""
    
    def __init__(self, message: str, path: Optional[str] = None, 
                 context: Optional[Dict[str, Any]] = None):
        context = context or {}
        if path:
            context['path'] = path
        super().__init__(message, ExitCode.PATH_ERROR, context)


class DeletionSafetyError(LazyScanError):
    """Raised when a deletion operation is blocked for safety reasons."""
    
    def __init__(self, message: str, path: Optional[str] = None,
                 reason: Optional[str] = None, context: Optional[Dict[str, Any]] = None):
        context = context or {}
        if path:
            context['path'] = path
        if reason:
            context['safety_reason'] = reason
        
        user_msg = f"Deletion blocked for safety: {message}"
        super().__init__(message, ExitCode.DELETION_ERROR, context, user_msg)


class SecurityPolicyError(LazyScanError):
    """Raised when a security policy violation occurs or policy system fails."""
    
    def __init__(self, message: str, policy_hash: Optional[str] = None,
                 context: Optional[Dict[str, Any]] = None):
        context = context or {}
        if policy_hash:
            context['policy_hash'] = policy_hash
        
        user_msg = f"Security policy violation: {message}"
        super().__init__(message, ExitCode.SECURITY_ERROR, context, user_msg)


class UnsupportedPlatformError(LazyScanError):
    """Raised when operation is not supported on current platform."""
    
    def __init__(self, message: str, platform: Optional[str] = None,
                 operation: Optional[str] = None, context: Optional[Dict[str, Any]] = None):
        context = context or {}
        if platform:
            context['platform'] = platform
        if operation:
            context['operation'] = operation
        
        user_msg = f"Platform not supported: {message}"
        super().__init__(message, ExitCode.PLATFORM_ERROR, context, user_msg)


class DiscoveryError(LazyScanError):
    """Raised when project discovery fails."""
    
    def __init__(self, message: str, search_paths: Optional[List[str]] = None,
                 app_type: Optional[str] = None, context: Optional[Dict[str, Any]] = None):
        context = context or {}
        if search_paths:
            context['search_paths'] = search_paths
        if app_type:
            context['app_type'] = app_type
        
        user_msg = f"Project discovery failed: {message}"
        super().__init__(message, ExitCode.DISCOVERY_ERROR, context, user_msg)


class ConfigError(LazyScanError):
    """Raised when configuration is invalid."""
    
    def __init__(self, message: str, config_file: Optional[str] = None,
                 context: Optional[Dict[str, Any]] = None):
        context = context or {}
        if config_file:
            context['config_file'] = config_file
        
        user_msg = f"Configuration error: {message}"
        super().__init__(message, ExitCode.CONFIG_ERROR, context, user_msg)


class UserAbortedError(LazyScanError):
    """Raised when user cancels an operation."""
    
    def __init__(self, message: str = "Operation cancelled by user", 
                 operation: Optional[str] = None, context: Optional[Dict[str, Any]] = None):
        context = context or {}
        if operation:
            context['operation'] = operation
        
        super().__init__(message, ExitCode.USER_CANCELLED, context)


class PermissionError(LazyScanError):
    """Raised when file/directory permissions prevent operation."""
    
    def __init__(self, message: str, path: Optional[str] = None,
                 context: Optional[Dict[str, Any]] = None):
        context = context or {}
        if path:
            context['path'] = path
        
        user_msg = f"Permission denied: {message}"
        super().__init__(message, ExitCode.PERMISSION_ERROR, context, user_msg)


class ValidationError(LazyScanError):
    """Raised when input validation fails."""
    
    def __init__(self, message: str, field: Optional[str] = None,
                 value: Optional[str] = None, context: Optional[Dict[str, Any]] = None):
        context = context or {}
        if field:
            context['field'] = field
        if value:
            context['value'] = value
        
        user_msg = f"Validation error: {message}"
        super().__init__(message, ExitCode.VALIDATION_ERROR, context, user_msg)


class NetworkError(LazyScanError):
    """Raised when network operations fail."""
    
    def __init__(self, message: str, url: Optional[str] = None,
                 context: Optional[Dict[str, Any]] = None):
        context = context or {}
        if url:
            context['url'] = url
        
        user_msg = f"Network error: {message}"
        super().__init__(message, ExitCode.NETWORK_ERROR, context, user_msg)


class DependencyError(LazyScanError):
    """Raised when required dependencies are missing."""
    
    def __init__(self, message: str, dependency: Optional[str] = None,
                 context: Optional[Dict[str, Any]] = None):
        context = context or {}
        if dependency:
            context['dependency'] = dependency
        
        user_msg = f"Missing dependency: {message}"
        super().__init__(message, ExitCode.DEPENDENCY_ERROR, context, user_msg)


# Error handling utilities

def handle_exception(exc: Exception, logger, operation: str = "unknown", re_raise: bool = True) -> Dict[str, Any]:
    """
    Handle an exception with structured logging and context extraction.
    
    Args:
        exc: Exception to handle
        logger: Logger instance to use for logging
        operation: Name of operation that failed
        re_raise: Whether to re-raise the exception after logging
        
    Returns:
        Dict containing exception details for further processing
    """
    if isinstance(exc, LazyScanError):
        # Our custom exception with structured data
        exc_data = exc.to_dict()
        exc_data['operation'] = operation
        
        # Try to use structured logging if available
        try:
            from .logging_config import get_logger, log_security_event
            
            # If we have a structured logger, use it directly
            if hasattr(logger, '_log') and hasattr(logger, 'logger'):
                structured_logger = logger
            else:
                # Create a structured logger from the provided logger's name
                logger_name = getattr(logger, 'name', 'lazyscan.errors')
                structured_logger = get_logger(logger_name)
            
            # Log with structured logger
            # Remove 'message' key to avoid conflict with positional parameter
            log_data = {k: v for k, v in exc_data.items() if k != 'message'}
            structured_logger.error(f"Operation '{operation}' failed", **log_data)
            
            # If it's a security-related exception, also log to audit trail
            if isinstance(exc, (SecurityPolicyError, DeletionSafetyError)):
                # Create audit data without conflicting keys
                audit_data = {k: v for k, v in exc_data.items() if k not in ['operation']}
                log_security_event(
                    event_type='exception_occurred',
                    severity='error',
                    description=f"Security exception in {operation}: {exc.user_message}",
                    operation=operation,
                    **audit_data
                )
        except ImportError:
            # Fallback to standard logging
            logger.error(
                f"Operation '{operation}' failed: {exc.user_message}",
                extra=exc_data
            )
        
        if re_raise:
            raise exc
        
        return exc_data
    else:
        # Generic exception - extract what we can
        exc_data = {
            'exception_type': exc.__class__.__name__,
            'message': str(exc),
            'operation': operation,
            'exit_code': ExitCode.GENERAL_ERROR
        }
        
        # Try structured logging
        try:
            from .logging_config import get_logger
            
            if hasattr(logger, '_log') and hasattr(logger, 'logger'):
                structured_logger = logger
            else:
                logger_name = getattr(logger, 'name', 'lazyscan.errors')
                structured_logger = get_logger(logger_name)
            
            # Remove 'message' key to avoid conflict with positional parameter
            log_data = {k: v for k, v in exc_data.items() if k != 'message'}
            structured_logger.error(f"Unexpected error in operation '{operation}'", **log_data)
        except ImportError:
            # Fallback to standard logging
            logger.error(
                f"Unexpected error in operation '{operation}': {exc}",
                extra=exc_data,
                exc_info=True
            )
        
        if re_raise:
            raise exc
        
        return exc_data


def format_user_error(exc: Exception) -> str:
    """
    Format an exception for user display with helpful context.
    
    Args:
        exc: Exception to format
        
    Returns:
        User-friendly error message
    """
    if isinstance(exc, LazyScanError):
        message = f"❌ {exc.user_message}"
        
        # Add helpful context
        if 'path' in exc.context:
            message += f"\n   Path: {exc.context['path']}"
        if 'operation' in exc.context:
            message += f"\n   Operation: {exc.context['operation']}"
        
        # Add suggestions based on error type
        if isinstance(exc, PathValidationError):
            message += "\n\n💡 Check that the path exists and you have permission to access it."
        elif isinstance(exc, SecurityPolicyError):
            message += "\n\n💡 Review security policy or use --help for safe alternatives."
        elif isinstance(exc, DeletionSafetyError):
            message += "\n\n💡 Use --dry-run to preview deletions safely."
        elif isinstance(exc, UserAbortedError):
            message += "\n\n💡 Operation cancelled successfully."
        
        return message
    else:
        return f"❌ Unexpected error: {exc}"


import time
import random
from typing import Callable, TypeVar, Union

T = TypeVar('T')


def retry_with_backoff(
    func: Callable[[], T],
    max_attempts: int = 3,
    base_delay: float = 0.5,
    max_delay: float = 5.0,
    backoff_factor: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: tuple = (OSError, IOError, PermissionError)
) -> T:
    """
    Retry a function with exponential backoff for transient failures.
    
    Args:
        func: Function to retry
        max_attempts: Maximum number of attempts
        base_delay: Base delay between attempts (seconds)
        max_delay: Maximum delay between attempts (seconds)
        backoff_factor: Factor to multiply delay by each attempt
        jitter: Whether to add random jitter to delay
        retryable_exceptions: Tuple of exception types to retry on
        
    Returns:
        Result of successful function call
        
    Raises:
        Original exception if all attempts fail
    """
    last_exception = None
    delay = base_delay
    
    for attempt in range(1, max_attempts + 1):
        try:
            return func()
        except retryable_exceptions as e:
            last_exception = e
            
            if attempt == max_attempts:
                # Final attempt - re-raise the exception
                raise
            
            # Calculate delay with jitter
            actual_delay = delay
            if jitter:
                actual_delay *= (0.5 + random.random())  # 50-150% of base delay
            actual_delay = min(actual_delay, max_delay)
            
            # Log retry attempt
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(
                f"Attempt {attempt}/{max_attempts} failed, retrying in {actual_delay:.2f}s: {e}",
                extra={
                    'attempt': attempt,
                    'max_attempts': max_attempts,
                    'delay': actual_delay,
                    'exception_type': e.__class__.__name__
                }
            )
            
            time.sleep(actual_delay)
            delay = min(delay * backoff_factor, max_delay)
        
        except Exception:
            # Non-retryable exception - re-raise immediately
            raise
    
    # Should not reach here, but if we do, raise the last exception
    if last_exception:
        raise last_exception
    else:
        raise RuntimeError("Retry logic error - no exception to re-raise")


def safe_operation(operation_name: str, func: Callable[[], T], logger, 
                  retryable: bool = False, **retry_kwargs) -> T:
    """
    Execute an operation with comprehensive error handling and optional retry.
    
    Args:
        operation_name: Name of operation for logging
        func: Function to execute
        logger: Logger instance
        retryable: Whether to retry on transient failures
        **retry_kwargs: Arguments for retry_with_backoff
        
    Returns:
        Result of successful operation
        
    Raises:
        Exception from the operation (possibly after retries)
    """
    logger.debug(f"Starting operation: {operation_name}")
    
    try:
        if retryable:
            result = retry_with_backoff(func, **retry_kwargs)
        else:
            result = func()
        
        logger.debug(f"Operation '{operation_name}' completed successfully")
        return result
        
    except Exception as e:
        # Log the error with context
        handle_exception(e, logger, operation_name)
        raise


def cli_error_handler(func: Callable) -> Callable:
    """
    Decorator for CLI entry points to handle errors gracefully.
    
    This decorator:
    - Catches all exceptions
    - Logs them with structured context
    - Displays user-friendly error messages
    - Exits with appropriate exit codes
    """
    def wrapper(*args, **kwargs):
        try:
            # Import console adapter for user-facing messages
            from .logging_config import get_console
            console = get_console()
            
            return func(*args, **kwargs)
        except KeyboardInterrupt:
            console.print_error("\n💔 Operation interrupted by user")
            sys.exit(ExitCode.USER_CANCELLED)
        except LazyScanError as e:
            # Our custom exceptions - format and display user-friendly error
            formatted_error = format_user_error(e)
            console.print_error(formatted_error)
            sys.exit(e.exit_code)
        except Exception as e:
            # Unexpected exceptions
            console.print_error(f"❌ Unexpected error: {e}")
            console.print_error("\n🔍 For debugging, run with --log-level=DEBUG")
            
            # Log full traceback for debugging with structured logger
            try:
                from .logging_config import get_logger
                logger = get_logger(func.__module__)
            except ImportError:
                # Fallback to standard logging
                import logging
                logger = logging.getLogger(func.__module__)
            
            logger.error(
                f"Unexpected exception in {func.__name__}",
                function_name=func.__name__,
                module=func.__module__,
                exception_type=e.__class__.__name__,
                exception_message=str(e)
            )
            
            sys.exit(ExitCode.GENERAL_ERROR)
    
    return wrapper


def validate_not_none(value: Any, name: str) -> Any:
    """
    Validate that a value is not None.
    
    Args:
        value: Value to check
        name: Name of the value for error reporting
        
    Returns:
        The value if not None
        
    Raises:
        ValidationError: If value is None
    """
    if value is None:
        raise ValidationError(f"{name} cannot be None", field=name)
    return value


def validate_file_exists(path: str, operation: str = "operation") -> str:
    """
    Validate that a file exists.
    
    Args:
        path: Path to check
        operation: Operation name for error context
        
    Returns:
        The path if file exists
        
    Raises:
        PathValidationError: If file doesn't exist
    """
    from pathlib import Path
    
    path_obj = Path(path)
    if not path_obj.exists():
        raise PathValidationError(
            f"File not found for {operation}",
            path=path,
            context={'operation': operation}
        )
    
    return path


def validate_directory_exists(path: str, operation: str = "operation") -> str:
    """
    Validate that a directory exists.
    
    Args:
        path: Path to check  
        operation: Operation name for error context
        
    Returns:
        The path if directory exists
        
    Raises:
        PathValidationError: If directory doesn't exist
    """
    from pathlib import Path
    
    path_obj = Path(path)
    if not path_obj.exists():
        raise PathValidationError(
            f"Directory not found for {operation}",
            path=path,
            context={'operation': operation}
        )
    
    if not path_obj.is_dir():
        raise PathValidationError(
            f"Path is not a directory for {operation}",
            path=path,
            context={'operation': operation, 'is_file': path_obj.is_file()}
        )
    
    return path
