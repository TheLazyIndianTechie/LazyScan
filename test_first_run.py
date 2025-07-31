#!/usr/bin/env python3
"""Test script to verify disclaimer first-run behavior."""

import os
import subprocess
import sys
import shutil

# Path to config file
CONFIG_DIR = os.path.expanduser('~/.config/lazyscan')
CONFIG_FILE = os.path.join(CONFIG_DIR, 'preferences.ini')

def cleanup_config():
    """Remove config file to simulate first run."""
    if os.path.exists(CONFIG_FILE):
        os.remove(CONFIG_FILE)
        print(f"✓ Removed config file: {CONFIG_FILE}")
    else:
        print(f"ℹ Config file doesn't exist: {CONFIG_FILE}")

def run_lazyscan_test(test_name, args=None):
    """Run lazyscan and capture output."""
    print(f"\n{'='*60}")
    print(f"TEST: {test_name}")
    print('='*60)
    
    cmd = [sys.executable, 'lazyscan.py']
    if args:
        cmd.extend(args)
    
    # Run with a non-interactive input to simulate pressing Enter
    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    
    # Send Enter key to acknowledge disclaimer if needed
    output, _ = process.communicate(input='\n')
    
    # Check if disclaimer was shown
    has_disclaimer = 'DISCLAIMER' in output
    print(f"Disclaimer shown: {'YES' if has_disclaimer else 'NO'}")
    
    # Check if config file was created
    config_exists = os.path.exists(CONFIG_FILE)
    print(f"Config file created: {'YES' if config_exists else 'NO'}")
    
    return has_disclaimer, config_exists

def main():
    print("Testing LazyScan First-Run Disclaimer Behavior")
    print("=" * 60)
    
    # Test 1: First run (no config)
    cleanup_config()
    has_disclaimer1, config_exists1 = run_lazyscan_test(
        "First run - should show disclaimer",
        ['--version']
    )
    
    # Test 2: Second run (config exists)
    has_disclaimer2, config_exists2 = run_lazyscan_test(
        "Second run - should NOT show disclaimer",
        ['--no-logo', '--version']
    )
    
    # Test 3: Run with --no-logo (disclaimer should still respect first-run logic)
    cleanup_config()
    has_disclaimer3, config_exists3 = run_lazyscan_test(
        "First run with --no-logo - should NOT show disclaimer",
        ['--no-logo', '--version']
    )
    
    # Print summary
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print('='*60)
    print(f"Test 1 (First run): Disclaimer shown={has_disclaimer1}, Config created={config_exists1}")
    print(f"Test 2 (Second run): Disclaimer shown={has_disclaimer2}, Config exists={config_exists2}")
    print(f"Test 3 (--no-logo): Disclaimer shown={has_disclaimer3}, Config created={config_exists3}")
    
    # Verify results
    success = True
    if not has_disclaimer1:
        print("\n❌ FAIL: Disclaimer should be shown on first run")
        success = False
    if has_disclaimer2:
        print("\n❌ FAIL: Disclaimer should NOT be shown on second run")
        success = False
    if has_disclaimer3:
        print("\n❌ FAIL: Disclaimer should NOT be shown with --no-logo")
        success = False
        
    if success:
        print("\n✅ All tests passed!")
    else:
        print("\n❌ Some tests failed!")
    
    # Cleanup
    cleanup_config()

if __name__ == '__main__':
    main()
