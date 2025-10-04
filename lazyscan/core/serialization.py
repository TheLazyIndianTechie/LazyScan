"""
Serialization utilities for LazyScan using orjson.

Provides stable JSON schemas for ScanResult and cleanup summaries with
proper Unicode support and performance optimization.
"""

import dataclasses
from typing import Any, Dict, List, Tuple

import orjson

from .scan import ScanResult


def serialize_scan_result(scan_result: ScanResult) -> bytes:
    """
    Serialize ScanResult to JSON bytes using orjson.

    Args:
        scan_result: ScanResult instance to serialize

    Returns:
        JSON bytes with stable schema
    """
    data = scan_result_to_dict(scan_result)
    return orjson.dumps(data, option=orjson.OPT_NON_STR_KEYS | orjson.OPT_INDENT_2)


def scan_result_to_dict(scan_result: ScanResult) -> Dict[str, Any]:
    """
    Convert ScanResult to dictionary with stable schema.

    Schema:
    {
        "total_size_bytes": int,
        "file_count": int,
        "dir_count": int,
        "files": [{"path": str, "size_bytes": int}],
        "errors": [{"path": str, "error": str}],
        "scan_duration_seconds": float,
        "metadata": {...}
    }

    Args:
        scan_result: ScanResult instance

    Returns:
        Dictionary representation
    """
    return {
        "total_size_bytes": scan_result.total_size,
        "file_count": scan_result.file_count,
        "dir_count": scan_result.dir_count,
        "files": [
            {"path": path, "size_bytes": size}
            for path, size in scan_result.files
        ],
        "errors": [
            {"path": path, "error": error}
            for path, error in scan_result.errors
        ],
        "scan_duration_seconds": scan_result.scan_duration,
        "metadata": scan_result.metadata
    }


def serialize_cleanup_summary(summary: Dict[str, Any]) -> bytes:
    """
    Serialize cleanup summary to JSON bytes using orjson.

    Args:
        summary: Cleanup summary dictionary from RetentionPolicyEngine.get_cleanup_summary()

    Returns:
        JSON bytes with stable schema
    """
    return orjson.dumps(summary, option=orjson.OPT_NON_STR_KEYS | orjson.OPT_INDENT_2)


def deserialize_scan_result(json_bytes: bytes) -> ScanResult:
    """
    Deserialize JSON bytes back to ScanResult.

    Args:
        json_bytes: JSON bytes from serialize_scan_result()

    Returns:
        ScanResult instance

    Raises:
        ValueError: If JSON schema is invalid
    """
    try:
        data = orjson.loads(json_bytes)
        return dict_to_scan_result(data)
    except Exception as e:
        raise ValueError(f"Invalid ScanResult JSON: {e}")


def dict_to_scan_result(data: Dict[str, Any]) -> ScanResult:
    """
    Convert dictionary back to ScanResult.

    Args:
        data: Dictionary from scan_result_to_dict()

    Returns:
        ScanResult instance

    Raises:
        ValueError: If required fields are missing
    """
    required_fields = ["total_size_bytes", "file_count", "dir_count", "files", "errors", "scan_duration_seconds", "metadata"]

    for field in required_fields:
        if field not in data:
            raise ValueError(f"Missing required field: {field}")

    # Convert files and errors back to tuples
    files = [(item["path"], item["size_bytes"]) for item in data["files"]]
    errors = [(item["path"], item["error"]) for item in data["errors"]]

    return ScanResult(
        total_size=data["total_size_bytes"],
        file_count=data["file_count"],
        dir_count=data["dir_count"],
        files=files,
        errors=errors,
        scan_duration=data["scan_duration_seconds"],
        metadata=data["metadata"]
    )


def serialize_to_json(data: Any) -> str:
    """
    Serialize any data to JSON string with Unicode support.

    Args:
        data: Data to serialize

    Returns:
        JSON string
    """
    return orjson.dumps(data, option=orjson.OPT_NON_STR_KEYS).decode('utf-8')


def serialize_to_json_bytes(data: Any) -> bytes:
    """
    Serialize any data to JSON bytes with Unicode support.

    Args:
        data: Data to serialize

    Returns:
        JSON bytes
    """
    return orjson.dumps(data, option=orjson.OPT_NON_STR_KEYS)


# Schema documentation
SCAN_RESULT_SCHEMA = """
ScanResult JSON Schema:
{
  "type": "object",
  "properties": {
    "total_size_bytes": {"type": "integer", "description": "Total size of all files in bytes"},
    "file_count": {"type": "integer", "description": "Number of files found"},
    "dir_count": {"type": "integer", "description": "Number of directories found"},
    "files": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "path": {"type": "string", "description": "File path"},
          "size_bytes": {"type": "integer", "description": "File size in bytes"}
        },
        "required": ["path", "size_bytes"]
      }
    },
    "errors": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "path": {"type": "string", "description": "Path where error occurred"},
          "error": {"type": "string", "description": "Error message"}
        },
        "required": ["path", "error"]
      }
    },
    "scan_duration_seconds": {"type": "number", "description": "Time taken for scan in seconds"},
    "metadata": {"type": "object", "description": "Additional scan metadata"}
  },
  "required": ["total_size_bytes", "file_count", "dir_count", "files", "errors", "scan_duration_seconds", "metadata"]
}
"""

CLEANUP_SUMMARY_SCHEMA = """
Cleanup Summary JSON Schema:
{
  "type": "object",
  "properties": {
    "total_operations": {"type": "integer", "description": "Total number of cleanup operations"},
    "successful_operations": {"type": "integer", "description": "Number of successful operations"},
    "skipped_operations": {"type": "integer", "description": "Number of skipped operations"},
    "failed_operations": {"type": "integer", "description": "Number of failed operations"},
    "total_files_deleted": {"type": "integer", "description": "Total files deleted across all operations"},
    "total_size_mb": {"type": "number", "description": "Total size cleaned in MB"},
    "operations": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "target": {"type": "string", "description": "Target path cleaned"},
          "category": {"type": "string", "description": "Cache category"},
          "safety_level": {"type": "string", "description": "Safety level (safe, moderate, dangerous)"},
          "files_deleted": {"type": "integer", "description": "Files deleted in this operation"},
          "size_mb": {"type": "number", "description": "Size cleaned in MB"},
          "result": {"type": "string", "description": "Operation result"},
          "error_message": {"type": ["string", "null"], "description": "Error message if failed"}
        },
        "required": ["target", "category", "safety_level", "files_deleted", "size_mb", "result"]
      }
    }
  },
  "required": ["total_operations", "successful_operations", "skipped_operations", "failed_operations", "total_files_deleted", "total_size_mb", "operations"]
}
"""