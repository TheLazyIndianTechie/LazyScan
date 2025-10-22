#!/usr/bin/env python3
"""
User interface elements for LazyScan.
Logos, disclaimers, and visual display functions.
"""

import random

from ..core.logging_config import get_console

console = get_console()

# Funny messages for progress display
FUNNY_MESSAGES = [
    "Befriending disk sectors",
    "Convincing files to reveal their sizes",
    "Teaching directories about personal space",
    "Negotiating with storage drivers",
    "Asking nicely for file metadata",
    "Performing quantum size calculations",
    "Decoding file system hieroglyphics",
    "Measuring digital footprints",
    "Calculating byte-per-dollar ratios",
    "Investigating suspicious file activity",
]


def show_logo() -> None:
    """Display the LazyScan logo."""
    console.print(
        """
    ╔══════════════════════════════════════════════╗
    ║  LAZY SCAN - The Lazy Developer's Disk Tool  ║
    ║           Find what's eating your space      ║
    ╚══════════════════════════════════════════════╝
    """
    )


def show_disclaimer() -> None:
    """Display the usage disclaimer."""
    from ..core.formatting import get_terminal_colors

    colors = get_terminal_colors()
    (
        CYAN,
        MAGENTA,
        YELLOW,
        RESET,
        BOLD,
        BRIGHT_CYAN,
        BRIGHT_MAGENTA,
        GREEN,
        BLUE,
        RED,
    ) = colors

    console.print()
    console.print(
        f"{BOLD}{MAGENTA}╔═══════════════════════════════════════════════════════════════════════╗{RESET}"
    )
    console.print(
        f"{BOLD}{MAGENTA}║{RESET} {BRIGHT_CYAN}⚠️  LAZYSCAN DISCLAIMER AND SAFETY NOTICE ⚠️{RESET}                        {MAGENTA}║{RESET}"
    )
    console.print(
        f"{BOLD}{MAGENTA}╠═══════════════════════════════════════════════════════════════════════╣{RESET}"
    )
    console.print(
        f"{BOLD}{MAGENTA}║{RESET} {YELLOW}This tool is provided AS-IS for disk space analysis and cache{RESET}         {MAGENTA}║{RESET}"
    )
    console.print(
        f"{BOLD}{MAGENTA}║{RESET} {YELLOW}management. By using this tool, you acknowledge that:{RESET}                  {MAGENTA}║{RESET}"
    )
    console.print(
        f"{BOLD}{MAGENTA}║{RESET}                                                                        {MAGENTA}║{RESET}"
    )
    console.print(
        f"{BOLD}{MAGENTA}║{RESET} {CYAN}• Deleting cache files may affect application performance{RESET}              {MAGENTA}║{RESET}"
    )
    console.print(
        f"{BOLD}{MAGENTA}║{RESET} {CYAN}• Some applications may need to rebuild caches after deletion{RESET}          {MAGENTA}║{RESET}"
    )
    console.print(
        f"{BOLD}{MAGENTA}║{RESET} {CYAN}• Always verify files before deletion{RESET}                                  {MAGENTA}║{RESET}"
    )
    console.print(
        f"{BOLD}{MAGENTA}║{RESET} {CYAN}• The author is not responsible for any data loss{RESET}                      {MAGENTA}║{RESET}"
    )
    console.print(
        f"{BOLD}{MAGENTA}║{RESET}                                                                        {MAGENTA}║{RESET}"
    )
    console.print(
        f"{BOLD}{MAGENTA}║{RESET} {RED}⚠️  USE AT YOUR OWN RISK ⚠️{RESET}                                             {MAGENTA}║{RESET}"
    )
    console.print(
        f"{BOLD}{MAGENTA}╚═══════════════════════════════════════════════════════════════════════╝{RESET}"
    )
    console.print()


def get_random_funny_message() -> str:
    """Get a random funny message for progress display."""
    return random.choice(FUNNY_MESSAGES)


def knight_rider_animation(
    message: str,
    iterations: int = 3,
    animation_chars: str = "▮▯▯",
    delay: float = 0.07,
    colors=None,
) -> None:
    """Display Knight Rider style scanning animation."""
    import sys
    import time

    if colors is None:
        from ..core.formatting import get_terminal_colors

        colors = get_terminal_colors()

    CYAN, BRIGHT_MAGENTA, YELLOW, RESET, BOLD = colors[:5]

    if not sys.stdout.isatty():
        # Non-interactive mode - just print the message once
        console.print(f"{message}...")
        return

    width = 20

    for _ in range(iterations):
        # Move the scanner left to right
        for pos in range(width - len(animation_chars) + 1):
            scanner = (
                " " * pos + animation_chars + " " * (width - pos - len(animation_chars))
            )
            display = (
                f"{CYAN}[{BRIGHT_MAGENTA}{scanner}{CYAN}] {YELLOW}{message}{RESET}"
            )

            sys.stdout.write(f"\r{display}")
            sys.stdout.flush()
            time.sleep(delay)

        # Move the scanner right to left
        for pos in range(width - len(animation_chars), -1, -1):
            scanner = (
                " " * pos + animation_chars + " " * (width - pos - len(animation_chars))
            )
            display = (
                f"{CYAN}[{BRIGHT_MAGENTA}{scanner}{CYAN}] {YELLOW}{message}{RESET}"
            )

            sys.stdout.write(f"\r{display}")
            sys.stdout.flush()
            time.sleep(delay)

    # Clear the line
    sys.stdout.write(f"\r{' ' * (width + len(message) + 10)}\r")
    sys.stdout.flush()


def display_scan_results_header(file_count: int, colors: tuple[str, ...]) -> None:
    """Display the scan results header."""
    ACCENT_COLOR, HEADER_COLOR, BRIGHT_CYAN, RESET, BOLD = (
        colors[1],
        colors[2],
        colors[5],
        colors[3],
        colors[4],
    )

    console.print(
        f"\n{BOLD}{ACCENT_COLOR}┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓{RESET}"
    )
    console.print(
        f"{BOLD}{ACCENT_COLOR}┃ {HEADER_COLOR}TARGET ACQUIRED: {BRIGHT_CYAN}TOP {file_count} SPACE HOGS IDENTIFIED{ACCENT_COLOR} ┃{RESET}"
    )
    console.print(
        f"{BOLD}{ACCENT_COLOR}┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛{RESET}"
    )


def display_scan_summary(
    total_size: int, scan_path: str, colors: tuple[str, ...]
) -> None:
    """Display scan completion summary."""
    (
        ACCENT_COLOR,
        HEADER_COLOR,
        BRIGHT_CYAN,
        SIZE_COLOR,
        PATH_COLOR,
        YELLOW,
        GREEN,
        RESET,
    ) = (
        colors[1],
        colors[2],
        colors[5],
        colors[6],
        colors[7],
        colors[2],
        colors[7],
        colors[3],
    )

    from ..core.formatting import human_readable

    console.print(
        f"\n{ACCENT_COLOR}[{BRIGHT_CYAN}SYS{ACCENT_COLOR}] {HEADER_COLOR}Total data volume: {SIZE_COLOR}{human_readable(total_size)}{RESET}"
    )
    console.print(
        f"{ACCENT_COLOR}[{BRIGHT_CYAN}SYS{ACCENT_COLOR}] {HEADER_COLOR}Target directory: {PATH_COLOR}{scan_path}{RESET}"
    )
    console.print(
        f"{ACCENT_COLOR}[{BRIGHT_CYAN}SYS{ACCENT_COLOR}] {YELLOW}Scan complete. {GREEN}Have a nice day.{RESET}"
    )


def display_cache_cleanup_summary(
    freed_bytes: int,
    used_before: int,
    used_after: int,
    total_before: int,
    total_after: int,
    free_before: int,
    free_after: int,
    colors: tuple[str, ...],
) -> None:
    """Display cache cleanup summary banner."""
    from ..core.formatting import human_readable

    MAGENTA, YELLOW, BRIGHT_CYAN, BRIGHT_MAGENTA, GREEN, RESET, BOLD = (
        colors[1],
        colors[2],
        colors[5],
        colors[6],
        colors[7],
        colors[3],
        colors[4],
    )

    console.print(
        f"\n{BOLD}{MAGENTA}╔═══════════════════════════════════════════════════════════════════════╗{RESET}"
    )
    console.print(
        f"{BOLD}{MAGENTA}║ {BRIGHT_CYAN}CACHE CLEANUP SUMMARY {MAGENTA}║{RESET}"
    )
    console.print(
        f"{BOLD}{MAGENTA}╠═══════════════════════════════════════════════════════════════════════╣{RESET}"
    )
    console.print(
        f"{BOLD}{MAGENTA}║ {YELLOW}Space Freed:{RESET} {BRIGHT_MAGENTA}{human_readable(freed_bytes):>15}{RESET}                                        {MAGENTA}║{RESET}"
    )
    console.print(
        f"{BOLD}{MAGENTA}║ {YELLOW}Disk Used Before:{RESET} {BRIGHT_CYAN}{human_readable(used_before):>10}{RESET} ({(used_before/total_before*100):.1f}%)                        {MAGENTA}║{RESET}"
    )
    console.print(
        f"{BOLD}{MAGENTA}║ {YELLOW}Disk Used After:{RESET}  {GREEN}{human_readable(used_after):>10}{RESET} ({(used_after/total_after*100):.1f}%)                        {MAGENTA}║{RESET}"
    )
    console.print(
        f"{BOLD}{MAGENTA}║ {YELLOW}Free Space Gained:{RESET} {BRIGHT_MAGENTA}{human_readable(free_after - free_before):>9}{RESET}                                         {MAGENTA}║{RESET}"
    )
    console.print(
        f"{BOLD}{MAGENTA}╚═══════════════════════════════════════════════════════════════════════╝{RESET}"
    )
