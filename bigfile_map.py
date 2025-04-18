#!/usr/bin/env python3
"""
lazy-space: A lazy way to find what's eating your disk space.

Created by TheLazyIndianTechie - for the lazy developer in all of us.
"""
import os
import sys
import argparse
import time


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


def show_logo():
    """Display the lazy-space logo"""
    logo = r"""
 _               _____                     
| |    __ _ ____/ ___/  ___  ___ ____ ___ 
| |   / _` |_  /\___ \ / _ \/ _ `/ __/ -_)
|___| \__,_|/__/ ___/ \/ .__/\_,_/_/  \__/
                       /_/                 
    """
    print(logo)
    print("The lazy way to find what's eating your disk space.")
    print("Created by TheLazyIndianTechie\n")

def main():
    parser = argparse.ArgumentParser(
        description='A lazy way to find what\'s eating your disk space',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('-n', '--top', type=int, default=20,
                        help='number of top files to display (default: 20)')
    parser.add_argument('-w', '--width', type=int, default=40,
                        help='bar width in characters (default: 40)')
    parser.add_argument('-i', '--interactive', action='store_true',
                        help='prompt to choose directory (for the truly lazy)')
    parser.add_argument('--no-logo', action='store_true',
                        help='hide the lazy-space logo')
    parser.add_argument('path', nargs='?', default=None,
                        help='directory path to scan (default: current directory)')
    args = parser.parse_args()
    
    if not args.no_logo:
        show_logo()

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

    # Initialize terminal and progress display
    term_width = os.get_terminal_size().columns if sys.stdout.isatty() else 80
    use_progress = sys.stdout.isatty()  # Only use progress display on actual terminals
    
    # First pass to count total files for progress bar
    total_files = 0
    print(f"Counting files in '{scan_path}'...")
    for root, dirs, files in os.walk(scan_path):
        total_files += len(files)
    
    # Gather file sizes with progress indication
    file_sizes = []
    file_count = 0
    
    # Progress bar configuration
    bar_width = 30
    last_update_time = 0
    update_interval = 0.1  # seconds between updates, to avoid flicker
    
    # Start the scan with progress bar
    print(f"Scanning {total_files} files in '{scan_path}'...")
    
    # For throttling progress updates
    import time
    current_time = time.time()
    
    for root, dirs, files in os.walk(scan_path):
        rel_path = os.path.relpath(root, scan_path)
        rel_path = '.' if rel_path == '.' else f".../{rel_path}"
        
        for name in files:
            file_count += 1
            
            # Only update progress periodically to reduce terminal output
            current_time = time.time()
            should_update = (current_time - last_update_time) >= update_interval
            
            # Process the file
            full_path = os.path.join(root, name)
            try:
                size = os.path.getsize(full_path)
                file_sizes.append((full_path, size))
            except (OSError, PermissionError):
                continue
                
            # Update progress display if it's time
            if use_progress and (should_update or file_count == total_files):
                last_update_time = current_time
                
                # Calculate progress values
                percent = min(100, int(file_count / total_files * 100))
                filled_length = int(bar_width * file_count // total_files)
                bar = '█' * filled_length + '░' * (bar_width - filled_length)
                
                # Truncate path if needed
                max_path_len = term_width - 60
                if len(rel_path) > max_path_len:
                    show_path = "..." + rel_path[-max_path_len+3:]
                else:
                    show_path = rel_path
                
                # Create progress string
                progress_str = f"Scanning: [{bar}] {percent}% | {file_count}/{total_files} | {show_path}"
                
                # Use terminal control codes to update progress in place
                # Move cursor to beginning of line and clear the entire line
                sys.stdout.write("\033[1G\033[2K")
                sys.stdout.write(progress_str)
                sys.stdout.flush()
    
    # Display completion message
    if use_progress:
        sys.stdout.write("\033[1G\033[2K")  # Move to beginning of line and clear it
        sys.stdout.write(f"Completed: [{bar_width*'█'}] 100% | {file_count}/{total_files} files scanned.\n")
        sys.stdout.flush()
    
    if not file_sizes:
        print(f"No files found under '{scan_path}'.")
        return

    # Sort and select top N
    file_sizes.sort(key=lambda x: x[1], reverse=True)
    top_files = file_sizes[:args.top]
    max_size = top_files[0][1]

    # Render chart header
    print(f"\n{BAR_COLOR}Top {len(top_files)} space hogs found:{RESET}")
    print(f"{'#':>2}  {'Size Bar':<{args.width+2}}  {'Size':^10}  Path")
    print(f"{'-'*2}  {'-'*(args.width+2)}  {'-'*10}  {'-'*30}")
    
    # Render chart
    for idx, (path, size) in enumerate(top_files, start=1):
        bar_len = int((size / max_size) * args.width) if max_size > 0 else 0
        bar_full = BLOCK * bar_len
        bar_empty = ' ' * (args.width - bar_len)
        bar = f"{BAR_COLOR}{bar_full}{RESET}{bar_empty}"
        human = human_readable(size)
        size_str = f"{SIZE_COLOR}{human:>9}{RESET}"
        print(f"{idx:>2}. │{bar}│ {size_str} │ {path}")
    
    # Print total size info
    total_size = sum(size for _, size in top_files)
    print(f"\n{SIZE_COLOR}Total size of top {len(top_files)} files:{RESET} {human_readable(total_size)}")
    print(f"Scanned directory: {scan_path}")


if __name__ == '__main__':
    main()
