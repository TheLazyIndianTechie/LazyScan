#!/usr/bin/env python3
"""
User interface components for LazyScan.
Handles logo display, disclaimers, animations, and console interactions.
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple, Any, Optional
import shutil

from typing import Tuple

import random

from ..core.logging_config import get_console
from ..core.config import get_config

# Theme validation schemas
THEME_SCHEMA = {
    "primary": str,
    "accent": str,
    "warning": str,
    "success": str,
    "logo": list,
    "glyphs": dict,
    "animations": dict,
}

GLYPH_SCHEMA = {
    "scanner": str,
    "progress_filled": str,
    "progress_empty": str,
    "progress_medium": str,
    "progress_light": str,
    "file_python": str,
    "file_text": str,
    "file_archive": str,
    "file_generic": str,
    "file_directory": str,
}

ANIMATION_SCHEMA = {
    "knight_rider_delay": (int, float),
    "progress_update_interval": (int, float),
}


console = get_console()


@dataclass
class Theme:
    """Theme configuration for UI styling."""
    primary: str
    accent: str
    warning: str
    success: str
    logo: List[str]
    glyphs: Dict[str, str]
    animations: Dict[str, Any]


class ThemeManager:
    """Manages theme loading and application."""

    # Default cyberpunk theme
    DEFAULT_THEME = Theme(
        primary="\033[36m",  # CYAN
        accent="\033[35m",   # MAGENTA
        warning="\033[33m",  # YELLOW
        success="\033[92m",  # GREEN
        logo=[
            "╔══════════════════════════════════════════════╗",
            "║  LAZY SCAN - The Lazy Developer's Disk Tool  ║",
            "║           Find what's eating your space      ║",
            "╚══════════════════════════════════════════════╝",
        ],
        glyphs={
            "scanner": "▮▯▯",
            "progress_filled": "█",
            "progress_empty": "░",
            "progress_medium": "▓",
            "progress_light": "▒",
            "file_python": "🐍",
            "file_text": "📄",
            "file_archive": "📦",
            "file_generic": "📄",
            "file_directory": "📁",
        },
        animations={
            "knight_rider_delay": 0.07,
            "progress_update_interval": 0.1,
        }
    )

    @classmethod
    def load_theme(cls, theme_name: str = "default") -> Theme:
        """Load a theme by name, falling back to default if not found."""
        config = get_config()
        unicode_art_enabled = config.get("ui", {}).get("unicode_art", True)

        # Get theme data from config
        theme_data = config.get("themes", {}).get(theme_name, {})

        # Start with default theme values
        theme_dict = {
            "primary": cls.DEFAULT_THEME.primary,
            "accent": cls.DEFAULT_THEME.accent,
            "warning": cls.DEFAULT_THEME.warning,
            "success": cls.DEFAULT_THEME.success,
            "logo": cls.DEFAULT_THEME.logo.copy(),
            "glyphs": cls.DEFAULT_THEME.glyphs.copy(),
            "animations": cls.DEFAULT_THEME.animations.copy(),
        }

        # Override with configured values
        for key, value in theme_data.items():
            if key in theme_dict:
                theme_dict[key] = value

        # Apply Unicode art toggle
        if not unicode_art_enabled:
            theme_dict = cls._apply_ascii_fallbacks(theme_dict)

        return Theme(**theme_dict)

    @classmethod
    def _apply_ascii_fallbacks(cls, theme_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Apply ASCII-safe fallbacks when Unicode art is disabled."""
        # ASCII-safe logo
        theme_dict["logo"] = [
            "+----------------------------------------------+",
            "|  LAZY SCAN - The Lazy Developer's Disk Tool  |",
            "|           Find what's eating your space      |",
            "+----------------------------------------------+",
        ]

        # ASCII-safe glyphs
        ascii_glyphs = {
            "scanner": "[=]",
            "progress_filled": "#",
            "progress_empty": "-",
            "progress_medium": "=",
            "progress_light": "~",
            "file_python": "[PY]",
            "file_text": "[TXT]",
            "file_archive": "[ARC]",
            "file_generic": "[FIL]",
            "file_directory": "[DIR]",
        }

        # Update glyphs with ASCII fallbacks
        if "glyphs" in theme_dict and isinstance(theme_dict["glyphs"], dict):
            for glyph_key, ascii_value in ascii_glyphs.items():
                theme_dict["glyphs"][glyph_key] = ascii_value

        return theme_dict

    @classmethod
    def validate_theme_config(cls, config: Dict[str, Any]) -> List[str]:
        """Validate theme configuration and return list of errors."""
        errors = []

        if "themes" not in config:
            errors.append("Missing 'themes' section in configuration")
            return errors

        themes = config["themes"]
        if not isinstance(themes, dict):
            errors.append("'themes' must be a dictionary")
            return errors

        for theme_name, theme_data in themes.items():
            if not isinstance(theme_data, dict):
                errors.append(f"Theme '{theme_name}' must be a dictionary")
                continue

            # Validate theme structure
            for key, expected_type in THEME_SCHEMA.items():
                if key not in theme_data:
                    errors.append(f"Theme '{theme_name}' missing required key '{key}'")
                elif not isinstance(theme_data[key], expected_type):
                    errors.append(f"Theme '{theme_name}' key '{key}' must be of type {expected_type.__name__}")

            # Validate glyphs
            if "glyphs" in theme_data and isinstance(theme_data["glyphs"], dict):
                for glyph_key, expected_type in GLYPH_SCHEMA.items():
                    if glyph_key in theme_data["glyphs"]:
                        value = theme_data["glyphs"][glyph_key]
                        if not isinstance(value, expected_type):
                            errors.append(f"Theme '{theme_name}' glyph '{glyph_key}' must be of type {expected_type.__name__}")

            # Validate animations
            if "animations" in theme_data and isinstance(theme_data["animations"], dict):
                for anim_key, expected_types in ANIMATION_SCHEMA.items():
                    if anim_key in theme_data["animations"]:
                        value = theme_data["animations"][anim_key]
                        if not isinstance(value, expected_types):
                            type_names = [t.__name__ for t in expected_types] if isinstance(expected_types, tuple) else [expected_types.__name__]
                            errors.append(f"Theme '{theme_name}' animation '{anim_key}' must be of type {', '.join(type_names)}")

        return errors

    @classmethod
    def validate_config(cls, config: Dict[str, Any]) -> List[str]:
        """Validate the entire UI configuration including themes."""
        errors = []

        # Validate UI settings
        ui_config = config.get("ui", {})
        if not isinstance(ui_config, dict):
            errors.append("'ui' configuration must be a dictionary")
        else:
            # Validate unicode_art setting
            if "unicode_art" in ui_config:
                unicode_art = ui_config["unicode_art"]
                if not isinstance(unicode_art, bool):
                    errors.append("'ui.unicode_art' must be a boolean")

            # Validate theme setting
            if "theme" in ui_config:
                theme_name = ui_config["theme"]
                if not isinstance(theme_name, str):
                    errors.append("'ui.theme' must be a string")
                else:
                    # Check if theme exists
                    themes = config.get("themes", {})
                    if theme_name not in themes and theme_name != "default":
                        errors.append(f"Theme '{theme_name}' not found in themes configuration")

        # Validate themes
        errors.extend(cls.validate_theme_config(config))

        return errors

    @classmethod
    def get_current_theme(cls) -> Theme:
        """Get the currently configured theme."""
        config = get_config()
        theme_name = config.get("ui", {}).get("theme", "default")
        return cls.load_theme(theme_name)


# Global theme instance
_current_theme: Optional[Theme] = None


def get_theme() -> Theme:
    """Get the current theme, loading if necessary."""
    global _current_theme
    if _current_theme is None:
        _current_theme = ThemeManager.get_current_theme()
    return _current_theme


def get_terminal_size() -> Tuple[int, int]:
    """Get terminal dimensions with fallback."""
    try:
        size = shutil.get_terminal_size((120, 30))
        return size.columns, size.lines
    except (OSError, AttributeError):
        return 120, 30


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
    theme = get_theme()
    for line in theme.logo:
        console.print(line)


def show_disclaimer() -> None:
    """Display the usage disclaimer."""
    theme = get_theme()
    config = get_config()
    unicode_art = config.get("ui", {}).get("unicode_art", True)

    warning_emoji = "⚠️" if unicode_art else "WARNING"
    risk_emoji = "⚠️" if unicode_art else "WARNING"

    console.print()
    console.print(
        f"\033[1m{theme.accent}╔═══════════════════════════════════════════════════════════════════════╗\033[0m"
    )
    console.print(
        f"\033[1m{theme.accent}║\033[0m {theme.primary}{warning_emoji}  LAZYSCAN DISCLAIMER AND SAFETY NOTICE {warning_emoji}\033[0m                        {theme.accent}║\033[0m"
    )
    console.print(
        f"\033[1m{theme.accent}╠═══════════════════════════════════════════════════════════════════════╣\033[0m"
    )
    console.print(
        f"\033[1m{theme.accent}║\033[0m {theme.warning}This tool is provided AS-IS for disk space analysis and cache\033[0m{'':<9}{theme.accent}║\033[0m"
    )
    console.print(
        f"\033[1m{theme.accent}║\033[0m {theme.warning}management. By using this tool, you acknowledge that:\033[0m{'':<14}{theme.accent}║\033[0m"
    )
    console.print(
        f"\033[1m{theme.accent}║\033[0m{'':<79}{theme.accent}║\033[0m"
    )
    console.print(
        f"\033[1m{theme.accent}║\033[0m {theme.primary}• Deleting cache files may affect application performance\033[0m{'':<13}{theme.accent}║\033[0m"
    )
    console.print(
        f"\033[1m{theme.accent}║\033[0m {theme.primary}• Some applications may need to rebuild caches after deletion\033[0m{'':<9}{theme.accent}║\033[0m"
    )
    console.print(
        f"\033[1m{theme.accent}║\033[0m {theme.primary}• Always verify files before deletion\033[0m{'':<27}{theme.accent}║\033[0m"
    )
    console.print(
        f"\033[1m{theme.accent}║\033[0m {theme.primary}• The author is not responsible for any data loss\033[0m{'':<19}{theme.accent}║\033[0m"
    )
    console.print(
        f"\033[1m{theme.accent}║\033[0m{'':<79}{theme.accent}║\033[0m"
    )
    console.print(
        f"\033[1m{theme.accent}║\033[0m \033[91m{risk_emoji}  USE AT YOUR OWN RISK {risk_emoji}\033[0m{'':<29}{theme.accent}║\033[0m"
    )
    console.print(
        f"\033[1m{theme.accent}╚═══════════════════════════════════════════════════════════════════════╝\033[0m"
    )
    console.print()


def get_random_funny_message() -> str:
    """Get a random funny message for progress display."""
    return random.choice(FUNNY_MESSAGES)


def knight_rider_animation(
    message: str,
    iterations: int = 3,
    animation_chars: Optional[str] = None,
    delay: float = 0.07,
) -> None:
    """Display Knight Rider style scanning animation."""
    import sys
    import time

    theme = get_theme()
    config = get_config()

    if animation_chars is None:
        animation_chars = theme.glyphs.get("scanner", "▮▯▯")

    if delay is None:
        delay = float(theme.animations.get("knight_rider_delay", 0.07))

    if not sys.stdout.isatty() or not config.get("ui", {}).get("use_colors", True):
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
                f"{theme.primary}[{theme.accent}{scanner}{theme.primary}] {theme.warning}{message}\033[0m"
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
                f"{theme.primary}[{theme.accent}{scanner}{theme.primary}] {theme.warning}{message}\033[0m"
            )

            sys.stdout.write(f"\r{display}")
            sys.stdout.flush()
            time.sleep(delay)

    # Clear the line
    sys.stdout.write(f"\r{' ' * (width + len(message) + 10)}\r")
    sys.stdout.flush()


def display_scan_results_header(file_count: int, colors: Optional[Tuple[str, ...]] = None) -> None:
    """Display the scan results header."""
    if colors is None:
        theme = get_theme()
        # Create colors tuple from theme for backward compatibility
        colors = (
            "",  # index 0 (unused)
            theme.accent,  # ACCENT_COLOR
            theme.warning,  # HEADER_COLOR
            "\033[0m",  # RESET
            "\033[1m",  # BOLD
            theme.primary,  # BRIGHT_CYAN
        )

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
        f"{BOLD}{ACCENT_COLOR}┃ {HEADER_COLOR}TARGET ACQUIRED: {BRIGHT_CYAN}{file_count} SPACE HOGS IDENTIFIED{ACCENT_COLOR} ┃{RESET}"
    )
    console.print(
        f"{BOLD}{ACCENT_COLOR}┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛{RESET}"
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
    total_size: int, scan_path: str, colors: Optional[Tuple[str, ...]] = None
) -> None:
    """Display scan completion summary."""
    if colors is None:
        theme = get_theme()
        # Create colors tuple from theme for backward compatibility
        colors = (
            "",  # index 0 (unused)
            theme.accent,  # ACCENT_COLOR
            theme.warning,  # HEADER_COLOR
            "\033[0m",  # RESET
            "",  # index 4 (unused)
            theme.primary,  # BRIGHT_CYAN
            theme.primary,  # SIZE_COLOR
            theme.success,  # PATH_COLOR/GREEN
            theme.warning,  # YELLOW
            theme.success,  # GREEN
        )

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
        colors[8],
        colors[9],
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
    colors: Optional[Tuple[str, ...]] = None,
) -> None:
    """Display cache cleanup summary banner."""
    from ..core.formatting import human_readable

    if colors is None:
        theme = get_theme()
        # Create colors tuple from theme for backward compatibility
        colors = (
            "",  # index 0 (unused)
            theme.accent,  # MAGENTA
            theme.warning,  # YELLOW
            "\033[0m",  # RESET
            "\033[1m",  # BOLD
            theme.primary,  # BRIGHT_CYAN
            theme.primary,  # BRIGHT_MAGENTA (using primary for now)
            theme.success,  # GREEN
        )

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
