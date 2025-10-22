#!/usr/bin/env python3
"""
Formatting utilities for LazyScan.
Size formatting, progress bars, and display helpers.
"""

import os
import sys
import time
from typing import Optional


def human_readable(size: int) -> str:
    """Convert a size in bytes to a human-readable string."""
    for unit in ["B", "KB", "MB", "GB", "TB", "PB", "EB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} YB"


def get_terminal_colors(enable_colors: bool = True) -> tuple[str, ...]:
    """Get terminal color codes based on terminal support and user preference."""
    if enable_colors and sys.stdout.isatty():
        return (
            "\033[36m",  # CYAN
            "\033[35m",  # MAGENTA
            "\033[33m",  # YELLOW
            "\033[0m",  # RESET
            "\033[1m",  # BOLD
            "\033[96m",  # BRIGHT_CYAN
            "\033[95m",  # BRIGHT_MAGENTA
            "\033[92m",  # GREEN
            "\033[94m",  # BLUE
            "\033[91m",  # RED
        )
    else:
        return ("", "", "", "", "", "", "", "", "", "")


def format_progress_bar(
    current: int,
    total: int,
    width: int = 30,
    filled_char: str = "█",
    empty_char: str = "░",
) -> tuple[str, int]:
    """Create a formatted progress bar."""
    if total == 0:
        return empty_char * width, 0

    percent = min(100, int(current / total * 100))
    filled_length = int(width * current // total)
    bar = filled_char * filled_length + empty_char * (width - filled_length)

    return bar, percent


def truncate_path(path: str, max_length: int) -> str:
    """Truncate a path to fit within the specified length."""
    if len(path) <= max_length:
        return path

    if max_length <= 3:
        return "..."

    return "..." + path[-(max_length - 3) :]


class ProgressDisplay:
    """Manages terminal progress display with proper cleanup."""

    def __init__(self, enable_progress: bool = True):
        self.enable_progress = enable_progress and sys.stdout.isatty()
        self.last_update_time = 0
        self.update_interval = 0.1  # seconds between updates

    def update_progress(
        self,
        message: str,
        current: int,
        total: int,
        extra_info: str = "",
        force_update: bool = False,
    ) -> None:
        """Update progress display if conditions are met."""
        if not self.enable_progress:
            return

        current_time = time.time()
        should_update = (
            force_update
            or (current_time - self.last_update_time) >= self.update_interval
        )

        if should_update or current == total:
            self.last_update_time = current_time

            # Get terminal width for responsive display
            try:
                term_width = os.get_terminal_size().columns
            except OSError:
                term_width = 80

            # Create progress bar
            bar, percent = format_progress_bar(current, total)

            # Format the complete progress line
            if extra_info:
                progress_line = (
                    f"{message}: [{bar}] {percent}% | {current}/{total} | {extra_info}"
                )
            else:
                progress_line = f"{message}: [{bar}] {percent}% | {current}/{total}"

            # Truncate to terminal width if necessary
            if len(progress_line) > term_width - 1:
                progress_line = progress_line[: term_width - 4] + "..."

            # Clear line and write new progress
            sys.stdout.write("\033[2K\r")
            sys.stdout.write(progress_line)
            sys.stdout.flush()

    def finish_progress(self, completion_message: Optional[str] = None) -> None:
        """Finish progress display with optional completion message."""
        if not self.enable_progress:
            return

        # Clear line and optionally show completion message
        sys.stdout.write("\033[2K\r")
        if completion_message:
            sys.stdout.write(completion_message + "\n")
        else:
            sys.stdout.write("\n")
        sys.stdout.flush()


def format_file_table_header(width: int, colors: tuple[str, ...]) -> str:
    """Format the header for file listing table."""
    ACCENT_COLOR, HEADER_COLOR, RESET, BOLD = colors[1], colors[2], colors[3], colors[4]

    header = (
        f"{BOLD}{ACCENT_COLOR}┌─{'─'*2}──{'─'*(width+2)}──{'─'*10}──{'─'*30}─┐{RESET}\n"
    )
    header += f"{BOLD}{ACCENT_COLOR}│ {HEADER_COLOR}#{ACCENT_COLOR} │ {HEADER_COLOR}{'SIZE ALLOCATION':^{width}}{ACCENT_COLOR} │ {HEADER_COLOR}{'VOLUME':^10}{ACCENT_COLOR} │ {HEADER_COLOR}{'LOCATION PATH':^30}{ACCENT_COLOR} │{RESET}\n"
    header += (
        f"{BOLD}{ACCENT_COLOR}├─{'─'*2}──{'─'*(width+2)}──{'─'*10}──{'─'*30}─┤{RESET}"
    )

    return header


def format_file_table_row(
    idx: int, path: str, size: int, max_size: int, width: int, colors: tuple[str, ...]
) -> str:
    """Format a single row in the file listing table."""
    CYAN, MAGENTA, YELLOW, RESET, BOLD = colors[:5]
    if len(colors) > 5:
        BRIGHT_CYAN, BRIGHT_MAGENTA, GREEN = colors[5], colors[6], colors[7]
    else:
        BRIGHT_CYAN = BRIGHT_MAGENTA = GREEN = ""

    # Calculate bar representation
    bar_len = int((size / max_size) * width) if max_size > 0 else 0
    bar_full = "█" * bar_len
    bar_empty = "·" * (width - bar_len)
    bar = f"{BRIGHT_CYAN}{bar_full}{MAGENTA}{bar_empty}"

    # Format size
    human_size = human_readable(size)
    size_str = f"{BRIGHT_MAGENTA}{human_size:>9}{RESET}"

    # Format path (truncate if needed)
    path_display = truncate_path(path, 40)
    path_str = f"{GREEN}{path_display}{RESET}"

    # Pad path to fixed width
    padding = " " * (30 - len(path_display))

    return f"{BOLD}{MAGENTA}│ {YELLOW}{idx:>2}{MAGENTA} │ {bar} │ {size_str} │ {path_str}{padding}{MAGENTA} │{RESET}"


def format_file_table_footer(width: int, colors: tuple[str, ...]) -> str:
    """Format the footer for file listing table."""
    ACCENT_COLOR, RESET, BOLD = colors[1], colors[3], colors[4]
    return (
        f"{BOLD}{ACCENT_COLOR}└─{'─'*2}──{'─'*(width+2)}──{'─'*10}──{'─'*30}─┘{RESET}"
    )


def render_results_table(top_files: list, width: int, colors: tuple) -> None:
    """Render the complete results table with cyberpunk styling."""
    from ..core.logging_config import get_console

    console = get_console()

    if not top_files:
        return

    max_size = top_files[0][1]

    # Display table header
    console.print(format_file_table_header(width, colors))

    # Display each file row
    for idx, (path, size) in enumerate(top_files, start=1):
        console.print(format_file_table_row(idx, path, size, max_size, width, colors))

    # Display table footer
    console.print(format_file_table_footer(width, colors))
