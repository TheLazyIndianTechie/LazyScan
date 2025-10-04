#!/usr/bin/env python3
"""
Formatting utilities for LazyScan.
Size formatting, progress bars, and display helpers.
"""

import os
import sys
import time
import asyncio
from typing import Tuple, Optional, Dict, Any, List, Union


def human_readable(size: float) -> str:
    """Convert a size in bytes to a human-readable string."""
    current_size = float(size)
    for unit in ["B", "KB", "MB", "GB", "TB", "PB", "EB"]:
        if current_size < 1024:
            if current_size == int(current_size):
                return f"{int(current_size)} {unit}"
            else:
                return f"{current_size:.1f} {unit}"
        current_size /= 1024
    return f"{current_size:.1f} YB"


def parse_size(size_str: str) -> int:
    """Parse human-readable size string to bytes using humanfriendly.

    Supports formats like '1MB', '500KB', '2GB', '1.5TB', etc.
    Uses humanfriendly library for robust parsing.

    Args:
        size_str: Size string to parse (e.g., '1MB', '500KB', '2GB')

    Returns:
        Size in bytes as integer

    Raises:
        ValueError: If the size format is invalid

    Examples:
        >>> parse_size('1MB')
        1048576
        >>> parse_size('500KB')
        512000
        >>> parse_size('2GB')
        2147483648
    """
    if not size_str or size_str.strip() == "0B":
        return 0

    try:
        import humanfriendly
        return humanfriendly.parse_size(size_str)
    except ImportError:
        # Fallback to basic parsing if humanfriendly is not available
        return _parse_size_fallback(size_str)


def _parse_size_fallback(size_str: str) -> int:
    """Fallback size parsing implementation."""
    if not size_str:
        return 0

    # Remove spaces and convert to uppercase
    size_str = size_str.replace(" ", "").upper()

    # Extract number and unit
    import re
    match = re.match(r'^(\d+(?:\.\d+)?)([KMGT]?B?)$', size_str)
    if not match:
        raise ValueError(f"Invalid size format: {size_str}")

    number = float(match.group(1))
    unit = match.group(2)

    # Convert to bytes
    multipliers = {
        'B': 1,
        'KB': 1024,
        'MB': 1024**2,
        'GB': 1024**3,
        'TB': 1024**4,
    }

    # Handle cases like "1M" or "1MB"
    if unit in ['K', 'M', 'G', 'T']:
        unit += 'B'

    if unit not in multipliers:
        raise ValueError(f"Unknown size unit: {unit}")

    return int(number * multipliers[unit])


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
    width: Optional[int] = None,
    filled_char: str = "█",
    empty_char: str = "░",
    glyphs: Optional[Dict[str, str]] = None,
) -> Tuple[str, int]:
    """Create a formatted progress bar with responsive width."""
    # Use glyphs if provided
    if glyphs:
        filled_char = glyphs.get("progress_filled", filled_char)
        empty_char = glyphs.get("progress_empty", empty_char)

    if total == 0:
        width = width or 30
        return empty_char * width, 0

    # Calculate responsive width if not provided
    if width is None:
        try:
            term_width = os.get_terminal_size().columns
            # Reserve space for text and padding
            width = min(40, max(20, term_width - 40))
        except OSError:
            width = 30

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
    """Manages terminal progress display with proper cleanup and responsive layout using async scheduling."""

    def __init__(self, enable_progress: bool = True):
        self.enable_progress = enable_progress and sys.stdout.isatty()
        self.update_interval = 0.1  # seconds between updates
        self.pending_updates: List[Tuple[str, int, int, str]] = []
        self.last_emit = 0.0
        self._task: Optional[asyncio.Task] = None
        self._shutdown = False

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
            or (current_time - self.last_emit) >= self.update_interval
        )

        if should_update or current == total:
            self.last_emit = current_time
            self._render_progress(message, current, total, extra_info)

    async def update_progress_async(
        self,
        message: str,
        current: int,
        total: int,
        extra_info: str = "",
        force_update: bool = False,
    ) -> None:
        """Async version using asyncio.create_task scheduling for non-blocking UI updates."""
        if not self.enable_progress:
            return

        # Queue the update for batching
        self.pending_updates.append((message, current, total, extra_info))

        # Start batching task if not already running
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._batch_render())

    async def _batch_render(self) -> None:
        """Batch and render progress updates at regular intervals using asyncio scheduling."""
        try:
            while not self._shutdown and self.pending_updates:
                # Wait for batch interval to prevent UI flooding
                await asyncio.sleep(self.update_interval)

                # Get the latest update (discard intermediate ones for efficiency)
                if self.pending_updates:
                    message, current, total, extra_info = self.pending_updates[-1]
                    self.pending_updates.clear()

                    # Render the progress update
                    await asyncio.to_thread(self._render_progress, message, current, total, extra_info)

        except asyncio.CancelledError:
            # Render final update on cancellation
            if self.pending_updates and not self._shutdown:
                message, current, total, extra_info = self.pending_updates[-1]
                await asyncio.to_thread(self._render_progress, message, current, total, extra_info)
            raise

    async def finish_progress_async(self, completion_message: Optional[str] = None) -> None:
        """Finish async progress display with optional completion message."""
        if not self.enable_progress:
            return

        self._shutdown = True
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        # Clear line and optionally show completion message
        await asyncio.to_thread(self._finish_progress_sync, completion_message)

    def _finish_progress_sync(self, completion_message: Optional[str] = None) -> None:
        """Synchronous helper for finishing progress display."""
        # Clear line and optionally show completion message
        sys.stdout.write("\033[2K\r")
        if completion_message:
            sys.stdout.write(completion_message + "\n")
        else:
            sys.stdout.write("\n")
        sys.stdout.flush()

    def _render_progress(
        self,
        message: str,
        current: int,
        total: int,
        extra_info: str = "",
    ) -> None:
        """Internal method to render progress display."""
        # Get terminal width for responsive display
        try:
            term_width = os.get_terminal_size().columns
        except OSError:
            term_width = 80

        # Create responsive progress bar
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

        # Cleanup async state if needed
        self._shutdown = True
        if self._task and not self._task.done():
            self._task.cancel()


def format_file_table_header(width: Optional[int], colors: Tuple[str, ...]) -> str:
    """Format the header for file listing table with responsive width."""
    # Calculate responsive widths
    try:
        term_width = os.get_terminal_size().columns
    except OSError:
        term_width = 80

    if width is None:
        # Reserve space for borders, padding, and other columns
        available_width = max(20, term_width - 50)  # 50 for borders + other columns
        width = min(40, available_width)  # Cap at reasonable maximum

    # Adjust path column width based on terminal size
    path_width = max(20, min(50, term_width - width - 20))

    ACCENT_COLOR, HEADER_COLOR, RESET, BOLD = colors[1], colors[2], colors[3], colors[4]

    header = (
        f"{BOLD}{ACCENT_COLOR}┌─{'─'*2}──{'─'*(width+2)}──{'─'*10}──{'─'*path_width}─┐{RESET}\n"
    )
    header += f"{BOLD}{ACCENT_COLOR}│ {HEADER_COLOR}#{ACCENT_COLOR} │ {HEADER_COLOR}{'VISUAL SIZE':^{width}}{ACCENT_COLOR} │ {HEADER_COLOR}{'FILE SIZE':^10}{ACCENT_COLOR} │ {HEADER_COLOR}{'FILE PATH':^{path_width}}{ACCENT_COLOR} │{RESET}\n"
    header += (
        f"{BOLD}{ACCENT_COLOR}├─{'─'*2}──{'─'*(width+2)}──{'─'*10}──{'─'*path_width}─┤{RESET}"
    )

    return header


def format_file_table_row(
    idx: int, path: str, size: int, max_size: int, width: Optional[int], colors: Tuple[str, ...], glyphs: Optional[Dict[str, str]] = None
) -> str:
    """Format a single row in the file listing table with responsive width."""
    # Calculate responsive widths
    try:
        term_width = os.get_terminal_size().columns
    except OSError:
        term_width = 80

    if width is None:
        # Reserve space for borders, padding, and other columns
        available_width = max(20, term_width - 50)  # 50 for borders + other columns
        width = min(40, available_width)  # Cap at reasonable maximum

    # Adjust path column width based on terminal size
    path_width = max(20, min(50, term_width - width - 20))

    CYAN, MAGENTA, YELLOW, RESET, BOLD = colors[:5]
    if len(colors) > 5:
        BRIGHT_CYAN, BRIGHT_MAGENTA, GREEN, BLUE = colors[5], colors[6], colors[7], colors[8] if len(colors) > 8 else ""
    else:
        BRIGHT_CYAN = BRIGHT_MAGENTA = GREEN = BLUE = ""

    # Get glyph characters, with fallbacks
    progress_filled = glyphs.get("progress_filled", "█") if glyphs else "█"
    progress_medium = glyphs.get("progress_medium", "▓") if glyphs else "▓"
    progress_light = glyphs.get("progress_light", "▒") if glyphs else "▒"
    progress_empty = glyphs.get("progress_empty", "░") if glyphs else "░"

    # Calculate bar representation with gradient effect
    bar_len = int((size / max_size) * width) if max_size > 0 else 0
    if bar_len > 0:
        # Create gradient: full bars at start, then fading
        bar_full = progress_filled * min(bar_len, width//2)
        bar_medium = progress_medium * min(max(0, bar_len - width//2), width//4)
        bar_light = progress_light * min(max(0, bar_len - 3*width//4), width//4)
        bar_empty = progress_empty * (width - bar_len)
        bar = f"{BRIGHT_CYAN}{bar_full}{CYAN}{bar_medium}{MAGENTA}{bar_light}{RESET}{bar_empty}"
    else:
        bar = progress_empty * width

    # Format size with color coding based on size
    human_size = human_readable(size)
    if size > max_size * 0.8:
        size_color = BRIGHT_MAGENTA  # Largest files
    elif size > max_size * 0.5:
        size_color = CYAN  # Medium files
    else:
        size_color = GREEN  # Smaller files
    size_str = f"{size_color}{human_size:>9}{RESET}"

    # Format path with syntax highlighting
    path_display = truncate_path(path, path_width - 2)  # Account for icon

    # Add file type indicators using theme glyphs
    if path_display.endswith(('.py', '.pyc', '.pyo')):
        path_color = BLUE  # Python files
        file_icon = glyphs.get("file_python", "🐍") if glyphs else "🐍"
    elif path_display.endswith(('.log', '.txt', '.md')):
        path_color = GREEN  # Text files
        file_icon = glyphs.get("file_text", "📄") if glyphs else "📄"
    elif path_display.endswith(('.zip', '.tar', '.gz', '.rar')):
        path_color = YELLOW  # Archive files
        file_icon = glyphs.get("file_archive", "📦") if glyphs else "📦"
    elif '.' in path_display.split('/')[-1]:
        path_color = CYAN  # Other files with extension
        file_icon = glyphs.get("file_generic", "📄") if glyphs else "📄"
    else:
        path_color = MAGENTA  # Directories or extensionless files
        file_icon = glyphs.get("file_directory", "📁") if glyphs else "📁"

    path_str = f"{file_icon} {path_color}{path_display}{RESET}"

    # Pad path to calculated width
    padding = " " * max(0, path_width - len(path_display) - 2)  # Account for icon

    return f"{BOLD}{MAGENTA}│ {YELLOW}{idx:>2}{MAGENTA} │ {bar} │ {size_str} │ {path_str}{padding}{MAGENTA} │{RESET}"


def format_file_table_footer(width: Optional[int], colors: Tuple[str, ...]) -> str:
    """Format the footer for file listing table with responsive width."""
    # Calculate responsive widths
    try:
        term_width = os.get_terminal_size().columns
    except OSError:
        term_width = 80

    if width is None:
        # Reserve space for borders, padding, and other columns
        available_width = max(20, term_width - 50)  # 50 for borders + other columns
        width = min(40, available_width)  # Cap at reasonable maximum

    # Adjust path column width based on terminal size
    path_width = max(20, min(50, term_width - width - 20))

    ACCENT_COLOR, RESET, BOLD = colors[1], colors[3], colors[4]
    return (
        f"{BOLD}{ACCENT_COLOR}└─{'─'*2}──{'─'*(width+2)}──{'─'*10}──{'─'*path_width}─┘{RESET}"
    )


def render_results_table(
    top_files: List[Tuple[str, int]], width: Optional[int], colors: Tuple[str, ...], glyphs: Optional[Dict[str, str]] = None
) -> None:
    """Render the complete results table with cyberpunk styling and responsive layout."""
    from ..core.logging_config import get_console

    console = get_console()

    if not top_files:
        return

    max_size = top_files[0][1]

    # Display table header
    console.print(format_file_table_header(width, colors))

    # Display each file row
    for idx, (path, size) in enumerate(top_files, start=1):
        console.print(format_file_table_row(idx, path, size, max_size, width, colors, glyphs))

    # Display table footer
    console.print(format_file_table_footer(width, colors))
