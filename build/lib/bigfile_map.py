#!/usr/bin/env python3
"""
Generate a colorful, interactive bar chart of the biggest files in a directory tree.
"""
import os
import sys
import argparse


def human_readable(size):
    """Convert a size in bytes to a human-readable string."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB']:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} YB"


def select_directory():
    """Let the user choose a directory from stdin."""
    cwd = os.getcwd()
    dirs = ['.'] + sorted([d for d in os.listdir(cwd) if os.path.isdir(os.path.join(cwd, d))])
    print("Select directory to scan:")
    for idx, d in enumerate(dirs, start=1):
        print(f"  {idx}. {d}")
    print(f"  0. Enter custom path")
    while True:
        choice = input(f"Choice [0-{len(dirs)}]: ").strip()
        if not choice.isdigit():
            print("Please enter a number.")
            continue
        n = int(choice)
        if n == 0:
            custom = input("Enter path to scan: ").strip()
            return custom
        if 1 <= n <= len(dirs):
            return dirs[n-1]
        print(f"Invalid choice: {choice}")


def main():
    parser = argparse.ArgumentParser(
        description='Generate a colorful bar chart of the largest files'
    )
    parser.add_argument('-n', '--top', type=int, default=20,
                        help='number of top files to display')
    parser.add_argument('-w', '--width', type=int, default=40,
                        help='bar width in characters')
    parser.add_argument('-i', '--interactive', action='store_true',
                        help='prompt to choose directory')
    parser.add_argument('path', nargs='?', default=None,
                        help='directory path to scan')
    args = parser.parse_args()

    # Determine scan path
    if args.interactive:
        scan_path = select_directory()
    else:
        scan_path = args.path or '.'

    # Color support
    use_color = sys.stdout.isatty()
    if use_color:
        BAR_COLOR  = '\033[92m'  # light green
        SIZE_COLOR = '\033[1m'   # bold
        RESET      = '\033[0m'
    else:
        BAR_COLOR = SIZE_COLOR = RESET = ''
    BLOCK = '█'

    # Gather file sizes
    file_sizes = []
    for root, dirs, files in os.walk(scan_path):
        for name in files:
            full_path = os.path.join(root, name)
            try:
                size = os.path.getsize(full_path)
            except (OSError, PermissionError):
                continue
            file_sizes.append((full_path, size))
    if not file_sizes:
        print(f"No files found under '{scan_path}'.")
        return

    # Sort and select top N
    file_sizes.sort(key=lambda x: x[1], reverse=True)
    top_files = file_sizes[:args.top]
    max_size = top_files[0][1]

    # Render chart
    for idx, (path, size) in enumerate(top_files, start=1):
        bar_len = int((size / max_size) * args.width) if max_size > 0 else 0
        bar_full = BLOCK * bar_len
        bar_empty = ' ' * (args.width - bar_len)
        bar = f"{BAR_COLOR}{bar_full}{RESET}{bar_empty}"
        human = human_readable(size)
        size_str = f"{SIZE_COLOR}{human:>9}{RESET}"
        print(f"{idx:>2}. │{bar}│ {size_str} │ {path}")


if __name__ == '__main__':
    main()
