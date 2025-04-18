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
    """Display the lazy-space cyberpunk-style logo"""
    # Define ANSI color codes
    CYAN = '\033[36m'
    MAGENTA = '\033[35m'
    YELLOW = '\033[33m'
    GREEN = '\033[32m'
    BLUE = '\033[34m'
    RESET = '\033[0m'
    BOLD = '\033[1m'
    
    # Cyberpunk-style logo with gradient colors
    logo_lines = [
        f"{CYAN}    __{MAGENTA}___      {YELLOW}__{MAGENTA}___   {GREEN}______  {BLUE}__  __     {CYAN}______{MAGENTA}______    {RESET}",
        f"{CYAN}   /{MAGENTA}/   |    {YELLOW}/__{MAGENTA}/ /  {GREEN}/ ____/ {BLUE}/ / / /    {CYAN}/ ___/{MAGENTA}/ ____/    {RESET}",
        f"{CYAN}  / {MAGENTA}/ /| |  {YELLOW}__/__{MAGENTA}/ /  {GREEN}/___ \  {BLUE}/ /_/ /    {CYAN}\__ \{MAGENTA}/ /     {YELLOW}____{RESET}",
        f"{CYAN} / {MAGENTA}/_/ |_/ {YELLOW}/_/_{MAGENTA}  _/  {GREEN}____/ / {BLUE}/ __  /    {CYAN}___/ {MAGENTA}/ /___  {YELLOW}/ __/{RESET}",
        f"{CYAN}/__{MAGENTA}____/  {YELLOW}/_/{MAGENTA} /_/   {GREEN}/_____/ {BLUE}/_/ /_/    {CYAN}/____/{MAGENTA}\____/ {YELLOW}/_/   {RESET}"
    ]
    
    for line in logo_lines:
        print(line)
    
    print(f"\n{BOLD}{CYAN}[{MAGENTA}*{CYAN}]{RESET} {YELLOW}The next-gen tool for the {GREEN}lazy{YELLOW} developer who wants results {GREEN}fast{RESET}")
    print(f"{BOLD}{CYAN}[{MAGENTA}*{CYAN}]{RESET} {BLUE}Created by {MAGENTA}TheLazyIndianTechie{RESET} {YELLOW}// {GREEN}v0.1.3{RESET}\n")

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

    # Cyberpunk color scheme
    use_color = sys.stdout.isatty()
    if use_color:
        # Define cyberpunk-style color palette
        CYAN = '\033[36m'
        BRIGHT_CYAN = '\033[96m'
        MAGENTA = '\033[35m'
        BRIGHT_MAGENTA = '\033[95m'
        YELLOW = '\033[33m'
        GREEN = '\033[92m'
        BLUE = '\033[94m'
        RED = '\033[91m'
        BOLD = '\033[1m'
        RESET = '\033[0m'
        
        # Colors for specific elements
        BAR_COLOR = BRIGHT_CYAN
        SIZE_COLOR = BRIGHT_MAGENTA
        HEADER_COLOR = YELLOW
        PATH_COLOR = GREEN
        ACCENT_COLOR = MAGENTA
    else:
        # Fallback for non-terminal output
        CYAN = BRIGHT_CYAN = MAGENTA = BRIGHT_MAGENTA = YELLOW = GREEN = BLUE = RED = BOLD = RESET = ''
        BAR_COLOR = SIZE_COLOR = HEADER_COLOR = PATH_COLOR = ACCENT_COLOR = ''
    
    # Use full block character for the bar
    BLOCK = '█'

    # Initialize terminal and progress display
    term_width = os.get_terminal_size().columns if sys.stdout.isatty() else 80
    use_progress = sys.stdout.isatty()  # Only use progress display on actual terminals
    
    # First pass to count total files for progress bar with cyberpunk styling
    total_files = 0
    print(f"{BOLD}{CYAN}[{BRIGHT_MAGENTA}*{CYAN}]{RESET} {YELLOW}Initializing neural scan of {GREEN}'{scan_path}'{YELLOW}...{RESET}")
    for root, dirs, files in os.walk(scan_path):
        total_files += len(files)
    
    # Gather file sizes with progress indication
    file_sizes = []
    file_count = 0
    
    # Progress bar configuration
    bar_width = 30
    last_update_time = 0
    update_interval = 0.1  # seconds between updates, to avoid flicker
    
    # Start the scan with cyberpunk styling
    print(f"{BOLD}{CYAN}[{BRIGHT_MAGENTA}!{CYAN}]{RESET} {BRIGHT_CYAN}COMMENCING DEEP SCAN{RESET} of {YELLOW}{total_files}{RESET} files in {GREEN}'{scan_path}'{RESET}")
    print(f"{BOLD}{CYAN}[{BRIGHT_MAGENTA}>{CYAN}]{RESET} {YELLOW}Stand by for data analysis...{RESET}")
    
    # For throttling progress updates
    import time
    
    # Create a variable to track the single progress line
    progress_line = ""
    
    # IMPORTANT: Clear any previous output
    if use_progress:
        # First, write a blank line that will be our progress line
        sys.stdout.write("\n")
        # Then move cursor back up one line - this ensures we always have a line to write to
        sys.stdout.write("\033[1A")
        sys.stdout.flush()
    
    # Start tracking time for updates
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
                
                # Create cyberpunk-style progress string
                scan_symbol = "▓▒░" if file_count % 3 == 0 else "░▒▓" if file_count % 3 == 1 else "▒▓░"
                progress_str = f"{CYAN}[{BRIGHT_MAGENTA}{scan_symbol}{CYAN}] {BRIGHT_CYAN}SCANNING{RESET}: {BAR_COLOR}[{bar}]{RESET} {YELLOW}{percent}%{RESET} | {MAGENTA}{file_count}/{total_files}{RESET} | {GREEN}{show_path}{RESET}"
                
                # Use terminal control codes to FORCE single line updating
                # We'll use a different combination of escape codes that should work in all terminals
                # First we go to beginning of line and clear the entire line
                sys.stdout.write("\r")  # Just carriage return is most compatible
                # Write the new progress string
                sys.stdout.write(progress_str)
                # Clear anything that might be left on the line
                sys.stdout.write(" " * 20)  # Add extra spaces to cover any leftover characters
                # Go back to the end of our actual content
                sys.stdout.write("\r" + progress_str)
                sys.stdout.flush()
                
                # Add small delay to ensure terminal updates properly
                time.sleep(0.01)
    
    # Display cyberpunk-style completion message, using the same approach as the progress updates
    if use_progress:
        completion_msg = f"{CYAN}[{BRIGHT_MAGENTA}■■■{CYAN}] {BRIGHT_CYAN}SCAN COMPLETED{RESET}: {BAR_COLOR}[{bar_width*'█'}]{RESET} {YELLOW}100%{RESET} | {MAGENTA}{file_count}/{total_files}{RESET} files processed. {GREEN}Analysis ready.{RESET}"
        # Clear line with carriage return
        sys.stdout.write("\r")
        # Write completion message
        sys.stdout.write(completion_msg)
        # Clear anything that might be left on the line
        sys.stdout.write(" " * 30)
        # End with a newline for the next output
        sys.stdout.write("\n")
        sys.stdout.flush()
    
    if not file_sizes:
        print(f"No files found under '{scan_path}'.")
        return

    # Sort and select top N
    file_sizes.sort(key=lambda x: x[1], reverse=True)
    top_files = file_sizes[:args.top]
    max_size = top_files[0][1]

    # Render cyberpunk-style chart header with box drawing
    print(f"\n{BOLD}{ACCENT_COLOR}┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓{RESET}")
    print(f"{BOLD}{ACCENT_COLOR}┃ {HEADER_COLOR}TARGET ACQUIRED: {BRIGHT_CYAN}TOP {len(top_files)} SPACE HOGS IDENTIFIED{ACCENT_COLOR} ┃{RESET}")
    print(f"{BOLD}{ACCENT_COLOR}┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛{RESET}")
    
    # Table header with cyberpunk styling
    print(f"{BOLD}{ACCENT_COLOR}┌─{'─'*2}──{'─'*(args.width+2)}──{'─'*10}──{'─'*30}─┐{RESET}")
    print(f"{BOLD}{ACCENT_COLOR}│ {HEADER_COLOR}#{ACCENT_COLOR} │ {HEADER_COLOR}{'SIZE ALLOCATION':^{args.width}}{ACCENT_COLOR} │ {HEADER_COLOR}{'VOLUME':^10}{ACCENT_COLOR} │ {HEADER_COLOR}{'LOCATION PATH':^30}{ACCENT_COLOR} │{RESET}")
    print(f"{BOLD}{ACCENT_COLOR}├─{'─'*2}──{'─'*(args.width+2)}──{'─'*10}──{'─'*30}─┤{RESET}")
    
    # Render each file as a cyberpunk-style data entry
    for idx, (path, size) in enumerate(top_files, start=1):
        bar_len = int((size / max_size) * args.width) if max_size > 0 else 0
        
        # Use bright cyan for the progress bar with a glowing effect
        bar_full = BLOCK * bar_len
        bar_empty = '·' * (args.width - bar_len)  # Using dots instead of spaces for empty space
        bar = f"{BAR_COLOR}{bar_full}{ACCENT_COLOR}{bar_empty}"
        
        # Format size with bright magenta
        human = human_readable(size)
        size_str = f"{SIZE_COLOR}{human:>9}{RESET}"
        
        # Format path with green color
        path_display = path
        if len(path) > 40:
            path_display = "..." + path[-37:]
        
        # Print the row with cyberpunk styling
        print(f"{BOLD}{ACCENT_COLOR}│ {YELLOW}{idx:>2}{ACCENT_COLOR} │ {bar} │ {size_str} │ {PATH_COLOR}{path_display}{RESET}{' ' * (30 - len(path_display))}{ACCENT_COLOR} │{RESET}")
    
    # Close the table
    print(f"{BOLD}{ACCENT_COLOR}└─{'─'*2}──{'─'*(args.width+2)}──{'─'*10}──{'─'*30}─┘{RESET}")
    
    # Print total size info with cyberpunk styling
    total_size = sum(size for _, size in top_files)
    print(f"\n{ACCENT_COLOR}[{BRIGHT_CYAN}SYS{ACCENT_COLOR}] {HEADER_COLOR}Total data volume: {SIZE_COLOR}{human_readable(total_size)}{RESET}")
    print(f"{ACCENT_COLOR}[{BRIGHT_CYAN}SYS{ACCENT_COLOR}] {HEADER_COLOR}Target directory: {PATH_COLOR}{scan_path}{RESET}")
    print(f"{ACCENT_COLOR}[{BRIGHT_CYAN}SYS{ACCENT_COLOR}] {YELLOW}Scan complete. {GREEN}Have a nice day.{RESET}")


if __name__ == '__main__':
    main()
