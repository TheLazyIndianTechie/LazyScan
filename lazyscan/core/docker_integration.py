#!/usr/bin/env python3
"""
Docker integration for LazyScan cache management.
Provides Docker cleanup functionality with safety prompts and dry-run support.
"""

import subprocess
import re
from typing import Dict, Any, Optional, Tuple, List
from pathlib import Path

from ..core.logging_config import get_logger

logger = get_logger(__name__)


class DockerIntegration:
    """Handles Docker cache cleanup operations."""

    def __init__(self):
        """Initialize Docker integration."""
        self.docker_available = self._check_docker_availability()

    def _check_docker_availability(self) -> bool:
        """Check if Docker is available on the system."""
        try:
            result = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
            return False

    def is_available(self) -> bool:
        """Check if Docker integration is available."""
        return self.docker_available

    def get_system_df_info(self, dry_run: bool = True) -> Dict[str, Any]:
        """
        Get Docker system disk usage information.

        Args:
            dry_run: If True, only simulate the operation

        Returns:
            Dictionary with disk usage information
        """
        if not self.docker_available:
            return {"error": "Docker not available"}

        try:
            cmd = ["docker", "system", "df"]
            if dry_run:
                # In dry-run mode, just check if command would work
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode != 0:
                    return {"error": f"Docker command failed: {result.stderr.strip()}"}

                # Parse the output to get sizes
                lines = result.stdout.strip().split('\n')
                info = {"dry_run": True, "items": []}

                for line in lines[1:]:  # Skip header
                    if line.strip():
                        parts = re.split(r'\s{2,}', line.strip())
                        if len(parts) >= 3:
                            item = {
                                "type": parts[0],
                                "total_count": parts[1],
                                "active_count": parts[2] if len(parts) > 2 else "",
                                "size": parts[3] if len(parts) > 3 else "",
                                "reclaimable": parts[4] if len(parts) > 4 else ""
                            }
                            info["items"].append(item)

                return info
            else:
                # Actually run the command
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=30
                )

                if result.returncode != 0:
                    return {"error": f"Docker system df failed: {result.stderr.strip()}"}

                # Parse and return actual data
                return self._parse_system_df_output(result.stdout)

        except subprocess.TimeoutExpired:
            return {"error": "Docker command timed out"}
        except Exception as e:
            return {"error": f"Failed to get Docker disk usage: {str(e)}"}

    def _parse_system_df_output(self, output: str) -> Dict[str, Any]:
        """Parse docker system df output."""
        lines = output.strip().split('\n')
        result = {"items": []}

        for line in lines[1:]:  # Skip header
            if line.strip():
                parts = re.split(r'\s{2,}', line.strip())
                if len(parts) >= 3:
                    item = {
                        "type": parts[0],
                        "total_count": parts[1],
                        "active_count": parts[2] if len(parts) > 2 else "",
                        "size": parts[3] if len(parts) > 3 else "",
                        "reclaimable": parts[4] if len(parts) > 4 else ""
                    }
                    result["items"].append(item)

        return result

    def estimate_cleanup_size(self) -> Dict[str, Any]:
        """
        Estimate the size that would be freed by Docker cleanup.

        Returns:
            Dictionary with size estimates
        """
        if not self.docker_available:
            return {"error": "Docker not available", "estimated_mb": 0}

        try:
            # Run docker system df to get reclaimable sizes
            result = subprocess.run(
                ["docker", "system", "df"],
                capture_output=True,
                text=True,
                timeout=15
            )

            if result.returncode != 0:
                return {"error": f"Failed to get Docker info: {result.stderr.strip()}", "estimated_mb": 0}

            # Parse reclaimable sizes
            total_reclaimable_mb = 0
            lines = result.stdout.strip().split('\n')

            for line in lines[1:]:  # Skip header
                if line.strip():
                    parts = re.split(r'\s{2,}', line.strip())
                    if len(parts) >= 5:
                        reclaimable_str = parts[4]
                        if reclaimable_str and reclaimable_str != "0B":
                            mb_size = self._parse_size_to_mb(reclaimable_str)
                            total_reclaimable_mb += mb_size

            return {
                "estimated_mb": total_reclaimable_mb,
                "breakdown": self._parse_system_df_output(result.stdout)
            }

        except subprocess.TimeoutExpired:
            return {"error": "Docker command timed out", "estimated_mb": 0}
        except Exception as e:
            return {"error": f"Failed to estimate cleanup size: {str(e)}", "estimated_mb": 0}

    def _parse_size_to_mb(self, size_str: str) -> float:
        """Parse Docker size string to MB."""
        if not size_str or size_str == "0B":
            return 0.0

        # Remove any commas and extract number and unit
        size_str = size_str.replace(',', '')
        match = re.match(r'([\d.]+)\s*([A-Za-z]+)', size_str.strip())

        if not match:
            return 0.0

        value = float(match.group(1))
        unit = match.group(2).upper()

        # Convert to MB
        if unit == 'B':
            return value / (1024 * 1024)
        elif unit == 'KB':
            return value / 1024
        elif unit == 'MB':
            return value
        elif unit == 'GB':
            return value * 1024
        elif unit == 'TB':
            return value * 1024 * 1024
        else:
            # Unknown unit, assume MB
            return value

    def perform_cleanup(
        self,
        volumes: bool = False,
        dry_run: bool = True,
        force: bool = False
    ) -> Dict[str, Any]:
        """
        Perform Docker system cleanup.

        Args:
            volumes: Whether to clean up volumes (dangerous)
            dry_run: If True, only simulate the operation
            force: If True, skip confirmation prompts

        Returns:
            Dictionary with cleanup results
        """
        if not self.docker_available:
            return {"error": "Docker not available", "success": False}

        if volumes and not force:
            # Volume cleanup is dangerous, require explicit confirmation
            return {
                "error": "Volume cleanup requires explicit confirmation (--force flag)",
                "success": False,
                "requires_confirmation": True
            }

        try:
            # Build the command
            cmd = ["docker", "system", "prune", "--all"]
            if volumes:
                cmd.append("--volumes")

            if dry_run:
                # For dry run, just show what would be done
                cmd.append("--dry-run")

                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=30
                )

                return {
                    "success": result.returncode == 0,
                    "dry_run": True,
                    "command": " ".join(cmd),
                    "output": result.stdout.strip(),
                    "error": result.stderr.strip() if result.returncode != 0 else None
                }
            else:
                # Actually perform the cleanup
                logger.info(f"Running Docker cleanup: {' '.join(cmd)}")

                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 minutes timeout for cleanup
                )

                success = result.returncode == 0

                if success:
                    logger.info("Docker cleanup completed successfully")
                else:
                    logger.error(f"Docker cleanup failed: {result.stderr.strip()}")

                return {
                    "success": success,
                    "dry_run": False,
                    "command": " ".join(cmd),
                    "output": result.stdout.strip(),
                    "error": result.stderr.strip() if not success else None,
                    "space_reclaimed": self._extract_space_reclaimed(result.stdout) if success else 0
                }

        except subprocess.TimeoutExpired:
            return {"error": "Docker cleanup timed out", "success": False}
        except Exception as e:
            return {"error": f"Docker cleanup failed: {str(e)}", "success": False}

    def _extract_space_reclaimed(self, output: str) -> float:
        """Extract space reclaimed from docker prune output."""
        # Look for lines like "Total reclaimed space: 1.234GB"
        for line in output.split('\n'):
            if "Total reclaimed space:" in line:
                match = re.search(r'Total reclaimed space:\s*([\d.]+)\s*([A-Za-z]+)', line)
                if match:
                    value = float(match.group(1))
                    unit = match.group(2).upper()
                    return self._parse_size_to_mb(f"{value}{unit}")
        return 0.0

    def get_docker_info(self) -> Dict[str, Any]:
        """
        Get general Docker information.

        Returns:
            Dictionary with Docker system information
        """
        if not self.docker_available:
            return {"available": False, "error": "Docker not available"}

        try:
            # Get Docker version
            version_result = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )

            # Get system info
            info_result = subprocess.run(
                ["docker", "system", "info"],
                capture_output=True,
                text=True,
                timeout=10
            )

            return {
                "available": True,
                "version": version_result.stdout.strip() if version_result.returncode == 0 else "Unknown",
                "system_info": info_result.stdout.strip() if info_result.returncode == 0 else "Failed to get info"
            }

        except Exception as e:
            return {"available": False, "error": str(e)}