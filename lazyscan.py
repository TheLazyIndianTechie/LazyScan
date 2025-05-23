#!/usr/bin/env python3
"""
lazyscan: A lazy way to find what's eating your disk space.

Created by TheLazyIndianTechie - for the lazy developer in all of us.
v0.1.9
"""
import os
import sys
import argparse
import time
import random
import threading


def human_readable(size):
    """Convert a size in bytes to a human-readable string."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB']:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} YB"


def knight_rider_animation(message, iterations=3, animation_chars="▮▯▯", delay=0.07, colors=None):
    """Display a Knight Rider style animation while performing a task"""
    # Default colors if none provided
    if colors is None:
        # Neutral colors for fallback
        CYAN = MAGENTA = YELLOW = RESET = BOLD = ''
    else:
        CYAN, MAGENTA, YELLOW, RESET, BOLD = colors
        
    animation_width = 10
    for _ in range(iterations):
        # Knight Rider animation going right
        for i in range(animation_width):
            anim = "▯" * i + animation_chars + "▯" * (animation_width - i - len(animation_chars))
            sys.stdout.write(f"\r{BOLD}{CYAN}[{MAGENTA}{anim}{CYAN}]{RESET} {YELLOW}{message}{RESET}")
            sys.stdout.flush()
            time.sleep(delay)
        
        # Knight Rider animation going left
        for i in range(animation_width - 1, -1, -1):
            anim = "▯" * i + animation_chars + "▯" * (animation_width - i - len(animation_chars))
            sys.stdout.write(f"\r{BOLD}{CYAN}[{MAGENTA}{anim}{CYAN}]{RESET} {YELLOW}{message}{RESET}")
            sys.stdout.flush()
            time.sleep(delay)
    
    # Clear the animation line when done
    sys.stdout.write("\r" + " " * (len(message) + 30) + "\r")
    sys.stdout.flush()


# Funny messages for the scan
FUNNY_MESSAGES = [
    "Converting caffeine into code...",
    "Teaching AI to count without using fingers...",
    "Preparing to blame your downloads folder...",
    "Calculating how many cat videos you have...",
    "Checking if you've actually cleaned up those temp files...",
    "Looking for your 'definitely not important' folder...",
    "Finding where all those 'I'll sort this later' files went...",
    "Locating your digital hoarding evidence...",
    "Discovering what's actually filling up your drive...",
    "Searching for those 'I might need this someday' files...",
]


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
    """Display the lazyscan cyberpunk-style logo"""
    # Define ANSI color codes
    CYAN = '\033[36m'
    BRIGHT_CYAN = '\033[96m'
    MAGENTA = '\033[35m'
    BRIGHT_MAGENTA = '\033[95m'
    YELLOW = '\033[33m'
    GREEN = '\033[32m'
    BLUE = '\033[34m'
    RESET = '\033[0m'
    BOLD = '\033[1m'
    
    # Clear, modern ASCII art that clearly says "LAZY SCAN"
    logo_lines = [
        f"{CYAN}██{MAGENTA}      {BRIGHT_CYAN}█████{YELLOW}   {GREEN}███{BLUE}   {MAGENTA}██{BRIGHT_CYAN}     {YELLOW}███{GREEN}   {BLUE}██████{MAGENTA}    {BRIGHT_CYAN}█████{YELLOW}   {GREEN}██{BLUE}    {MAGENTA}██{BRIGHT_CYAN}",
        f"{CYAN}██{MAGENTA}      {BRIGHT_CYAN}██{YELLOW}  {GREEN}██{BLUE}  {MAGENTA}██{BRIGHT_CYAN} ██{YELLOW}  {GREEN}██{BLUE} {MAGENTA}██{BRIGHT_CYAN}    {YELLOW}██{GREEN} ██{BLUE}  {MAGENTA}██{BRIGHT_CYAN}  {YELLOW}██{GREEN}  {BLUE}██{MAGENTA}  {BRIGHT_CYAN}██{YELLOW} {GREEN}██{BLUE}   {MAGENTA}██{BRIGHT_CYAN}",
        f"{CYAN}██{MAGENTA}      {BRIGHT_CYAN}██{YELLOW}  {GREEN}██{BLUE}  {MAGENTA}██{BRIGHT_CYAN}███{YELLOW}   {GREEN}██{BLUE} {MAGENTA}██{BRIGHT_CYAN}    {YELLOW}██{GREEN}  {BLUE}█████{MAGENTA}   {BRIGHT_CYAN}█████{YELLOW}   {GREEN}██{BLUE}  {MAGENTA}██{BRIGHT_CYAN} ",
        f"{CYAN}██{MAGENTA}      {BRIGHT_CYAN}██{YELLOW}  {GREEN}██{BLUE}  {MAGENTA}██{BRIGHT_CYAN} ██{YELLOW}  {GREEN}██{BLUE} {MAGENTA}██{BRIGHT_CYAN}    {YELLOW}██{GREEN}    {BLUE}██{MAGENTA}    {BRIGHT_CYAN}██{YELLOW}  {GREEN}██{BLUE}  {MAGENTA}██{BRIGHT_CYAN} {YELLOW}██{GREEN} ",
        f"{CYAN}███████{MAGENTA} {BRIGHT_CYAN}█████{YELLOW}   {GREEN}██{BLUE}  {MAGENTA}██{BRIGHT_CYAN} {YELLOW} {GREEN}█████{BLUE}  {MAGENTA}██████{BRIGHT_CYAN} {YELLOW}██{GREEN}   {BLUE}██{MAGENTA}  {BRIGHT_CYAN}██{YELLOW}   {GREEN}██{BLUE} {MAGENTA}███████{BRIGHT_CYAN}",
    ]
    
    for line in logo_lines:
        print(line)
    
    print(f"\n{BOLD}{CYAN}[{MAGENTA}*{CYAN}]{RESET} {YELLOW}The next-gen tool for the {GREEN}lazy{YELLOW} developer who wants results {GREEN}fast{RESET}")
    print(f"{BOLD}{CYAN}[{MAGENTA}*{CYAN}]{RESET} {BLUE}Created by {MAGENTA}TheLazyIndianTechie{RESET} {YELLOW}// {GREEN}v0.1.8{RESET}\n")

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
                        help='hide the lazyscan logo')
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
    
    # First pass to count total files with Knight Rider animation
    total_files = 0
    
    # Display initial message
    print(f"{BOLD}{CYAN}[{BRIGHT_MAGENTA}*{CYAN}]{RESET} {YELLOW}Initializing neural scan of {GREEN}'{scan_path}'{YELLOW}...{RESET}")
    
    # Setup color pack for animation function
    color_pack = (CYAN, BRIGHT_MAGENTA, YELLOW, RESET, BOLD)
    
    # Select a random funny message
    funny_msg = random.choice(FUNNY_MESSAGES)
    
    # Start counting files with animation
    file_count_thread_active = True
    
    def count_files_task():
        nonlocal total_files
        for root, dirs, files in os.walk(scan_path):
            total_files += len(files)
            if not file_count_thread_active:
                break
    
    # Use threading to count files while showing animation
    file_count_thread = threading.Thread(target=count_files_task)
    file_count_thread.start()
    
    # Show animation while counting
    animation_count = 0
    while file_count_thread.is_alive():
        knight_rider_animation(funny_msg, iterations=1, colors=color_pack)
        animation_count += 1
        # Change the message occasionally for variety
        if animation_count % 3 == 0:
            funny_msg = random.choice(FUNNY_MESSAGES)
    
    file_count_thread_active = False
    file_count_thread.join()
    
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
    
    # Initialize progress display with a completely different terminal approach
    # This disables normal line buffering by using a special escape sequence
    if use_progress:
        # Print a specific message that will be overwritten
        print(f"{CYAN}[{BRIGHT_MAGENTA}···{CYAN}] {YELLOW}Preparing scan environment...{RESET}")
        # Now move cursor back up one line so we can overwrite it
        sys.stdout.write("\033[1A\r")
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
                
                # Use a more forceful approach to control the cursor and line updating
                # This clears the ENTIRE current line and moves cursor to beginning
                sys.stdout.write("\033[2K\r")
                
                # Now write the progress string
                sys.stdout.write(progress_str)
                sys.stdout.flush()
                
                # Add small delay to ensure terminal updates properly
                time.sleep(0.05)
    
    # Display cyberpunk-style completion message, using the same forceful approach
    if use_progress:
        completion_msg = f"{CYAN}[{BRIGHT_MAGENTA}■■■{CYAN}] {BRIGHT_CYAN}SCAN COMPLETED{RESET}: {BAR_COLOR}[{bar_width*'█'}]{RESET} {YELLOW}100%{RESET} | {MAGENTA}{file_count}/{total_files}{RESET} files processed. {GREEN}Analysis ready.{RESET}"
        
        # Clear entire line and move to beginning 
        sys.stdout.write("\033[2K\r")
        
        # Write completion message
        sys.stdout.write(completion_msg)
        
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
