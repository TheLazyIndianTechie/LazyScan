#!/usr/bin/env python3
"""
Core file system scanning functionality for LazyScan.
Handles directory traversal, file size calculation, and progress tracking.
"""

import os
import threading
from typing import Callable, Optional

from ..core.formatting import ProgressDisplay, human_readable
from ..core.logging_config import get_logger, log_context

logger = get_logger(__name__)


class FileScanner:
    """Core file scanning functionality with progress tracking."""

    def __init__(self):
        self.progress_display = ProgressDisplay()

    def count_files(self, scan_path: str) -> int:
        """Count total files in directory tree."""
        total_files = 0

        try:
            for root, dirs, files in os.walk(scan_path):
                total_files += len(files)
        except (OSError, PermissionError) as e:
            logger.warning(
                "Failed to count files in some directories",
                scan_path=scan_path,
                error=str(e),
            )

        return total_files

    def count_files_with_progress(
        self, scan_path: str, progress_callback: Optional[Callable[[str], None]] = None
    ) -> int:
        """Count files while showing progress animation."""
        total_files = 0
        file_count_active = True

        def count_task():
            nonlocal total_files
            try:
                for root, dirs, files in os.walk(scan_path):
                    if not file_count_active:
                        break
                    total_files += len(files)

                    if progress_callback:
                        rel_path = os.path.relpath(root, scan_path)
                        progress_callback(f"Counting files in {rel_path}")

            except (OSError, PermissionError) as e:
                logger.warning(
                    "Failed to count files", scan_path=scan_path, error=str(e)
                )

        # Run counting in background thread
        count_thread = threading.Thread(target=count_task)
        count_thread.start()
        count_thread.join()

        file_count_active = False
        return total_files

    def scan_files(
        self,
        scan_path: str,
        show_progress: bool = True,
        progress_message: str = "Scanning files",
    ) -> list[tuple[str, int]]:
        """
        Scan directory and return list of (file_path, size) tuples.

        Args:
            scan_path: Directory to scan
            show_progress: Whether to show progress display
            progress_message: Message to show during progress

        Returns:
            List of (file_path, size) tuples
        """
        with log_context(operation="file_scan", scan_path=scan_path):
            logger.info("Starting file scan", scan_path=scan_path)

            file_sizes = []
            file_count = 0

            # Count total files first if showing progress
            total_files = 0
            if show_progress:
                total_files = self.count_files(scan_path)
                logger.debug("File count completed", total_files=total_files)

            # Scan files with progress tracking
            try:
                for root, dirs, files in os.walk(scan_path):
                    rel_path = os.path.relpath(root, scan_path)
                    rel_path = "." if rel_path == "." else f".../{rel_path}"

                    for name in files:
                        file_count += 1
                        full_path = os.path.join(root, name)

                        try:
                            size = os.path.getsize(full_path)
                            file_sizes.append((full_path, size))

                        except (OSError, PermissionError) as e:
                            logger.debug(
                                "Failed to get file size",
                                file_path=full_path,
                                error=str(e),
                            )
                            continue

                        # Update progress display
                        if show_progress and total_files > 0:
                            self.progress_display.update_progress(
                                progress_message, file_count, total_files, rel_path
                            )

            except KeyboardInterrupt:
                logger.info("File scan interrupted by user", files_scanned=file_count)
                if show_progress:
                    self.progress_display.finish_progress("Scan interrupted")
                raise

            except Exception as e:
                logger.error("File scan failed", scan_path=scan_path, error=str(e))
                if show_progress:
                    self.progress_display.finish_progress("Scan failed")
                raise

            # Complete progress display
            if show_progress:
                self.progress_display.finish_progress(
                    f"Scan completed: {file_count} files processed"
                )

            logger.info(
                "File scan completed",
                scan_path=scan_path,
                files_found=len(file_sizes),
                total_size=sum(size for _, size in file_sizes),
            )

            return file_sizes

    def get_top_files(
        self, file_sizes: list[tuple[str, int]], count: int = 20
    ) -> list[tuple[str, int]]:
        """Get top N largest files from scan results."""
        if not file_sizes:
            return []

        # Sort by size (descending) and take top N
        sorted_files = sorted(file_sizes, key=lambda x: x[1], reverse=True)
        return sorted_files[:count]


class DiskUsageAnalyzer:
    """Analyzes disk usage and provides system information."""

    @staticmethod
    def get_disk_usage(path: str = "/") -> tuple[int, int, int, str]:
        """
        Get disk usage statistics for the given path.

        Returns:
            Tuple of (total, used, free, formatted_string)
        """
        try:
            statvfs = os.statvfs(path)
            total = statvfs.f_frsize * statvfs.f_blocks
            free = statvfs.f_frsize * statvfs.f_available
            used = total - free

            # Format as human-readable string
            usage_str = (
                f"Total: {human_readable(total)} | "
                f"Used: {human_readable(used)} ({used/total*100:.1f}%) | "
                f"Free: {human_readable(free)}"
            )

            return total, used, free, usage_str

        except (OSError, AttributeError) as e:
            logger.error("Failed to get disk usage", path=path, error=str(e))
            return 0, 0, 0, "Disk usage unavailable"


def scan_directory_interactive() -> str:
    """Interactive directory selection for scanning."""
    from ..core.logging_config import get_console

    console = get_console()

    try:
        import tkinter as tk
        from tkinter import filedialog

        # Create a root window (hidden)
        root = tk.Tk()
        root.withdraw()

        # Show directory selection dialog
        directory = filedialog.askdirectory(
            title="Select directory to scan", initialdir=os.path.expanduser("~")
        )

        root.destroy()

        if directory:
            logger.info("Directory selected via GUI", selected_path=directory)
            return directory
        else:
            console.print_info("No directory selected")
            return ""

    except ImportError:
        # Fallback to command-line input
        console.print_warning("GUI not available, using command-line input")

        while True:
            try:
                directory = input("Enter directory path to scan: ").strip()
                if not directory:
                    directory = "."

                if os.path.isdir(directory):
                    logger.info("Directory selected via CLI", selected_path=directory)
                    return directory
                else:
                    console.print_error(f"Directory does not exist: {directory}")

            except KeyboardInterrupt:
                console.print_info("\nOperation cancelled")
                return ""

    except Exception as e:
        logger.error("Directory selection failed", error=str(e))
        console.print_error(f"Directory selection failed: {e}")
        return ""


def count_files_in_directory(scan_path: str) -> int:
    """Count total files in directory tree."""
    total_files = 0

    try:
        for root, dirs, files in os.walk(scan_path):
            total_files += len(files)
    except (OSError, PermissionError) as e:
        logger.warning(
            "Failed to count files in some directories",
            scan_path=scan_path,
            error=str(e),
        )

    return total_files


def scan_directory_with_progress(
    scan_path: str, colors: tuple
) -> list[tuple[str, int]]:
    """Scan directory with progress display and return file sizes."""
    from ..core.formatting import truncate_path

    logger.info(
        "Starting directory scan with progress",
        extra={"scan_path": scan_path, "operation": "directory_scan"},
    )

    file_sizes = []

    # Count total files first
    total_files = count_files_in_directory(scan_path)

    if total_files == 0:
        logger.warning("No files found in directory", extra={"scan_path": scan_path})
        return []

    # Initialize progress display
    progress = ProgressDisplay()

    file_count = 0

    try:
        for root, dirs, files in os.walk(scan_path):
            rel_path = os.path.relpath(root, scan_path)
            rel_path = "." if rel_path == "." else f".../{rel_path}"

            for name in files:
                file_count += 1
                full_path = os.path.join(root, name)

                try:
                    size = os.path.getsize(full_path)
                    file_sizes.append((full_path, size))

                    # Update progress display
                    progress.update_progress(
                        "Scanning",
                        file_count,
                        total_files,
                        extra_info=truncate_path(rel_path, 30),
                    )

                except (OSError, PermissionError) as e:
                    logger.debug(
                        "Unable to get file size",
                        extra={"file_path": full_path, "error": str(e)},
                    )
                    continue

        # Complete progress display
        progress.finish_progress("Scan completed")

        logger.info(
            "Directory scan completed",
            extra={
                "scan_path": scan_path,
                "files_scanned": len(file_sizes),
                "total_files": total_files,
            },
        )

        return file_sizes

    except Exception as e:
        progress.finish_progress()
        logger.error(
            "Directory scan failed",
            extra={"scan_path": scan_path, "error": str(e)},
            exc_info=True,
        )
        raise


def get_disk_usage(path: str = "/") -> tuple[int, int, int, str]:
    """Get disk usage statistics for the given path."""
    analyzer = DiskUsageAnalyzer()
    return analyzer.get_disk_usage(path)


def default_directory_picker():
    """Default directory picker when other discovery methods fail."""
    from ..core.logging_config import get_console

    console = get_console()

    logger.info("Using default directory picker fallback")
    console.print("\nFalling back to manual directory selection...")

    cwd = os.getcwd()
    dirs = ["."] + sorted(
        [d for d in os.listdir(cwd) if os.path.isdir(os.path.join(cwd, d))]
    )
    console.print("Select directory to scan:")
    for idx, d in enumerate(dirs, start=1):
        console.print(f"  {idx}. {d}")
    console.print("  0. Enter custom path")

    while True:
        choice = input(f"Choice [0-{len(dirs)}]: ").strip()
        if not choice.isdigit():
            console.print("Please enter a number.")
            continue
        n = int(choice)
        if n == 0:
            custom = input("Enter path to scan: ").strip()
            logger.info("User selected custom path", extra={"path": custom})
            return custom
        if 1 <= n <= len(dirs):
            selected = dirs[n - 1]
            logger.info("User selected directory", extra={"directory": selected})
            return selected
        console.print(f"Invalid choice: {choice}")
