#!/usr/bin/env python3
"""Test script to verify disclaimer functionality"""

import sys
import os

# Add the current directory to Python path to import lazyscan
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the functions we want to test
from lazyscan import show_logo, show_disclaimer

print("Testing disclaimer display...")
print("=" * 80)
print("\n1. Testing show_logo():")
print("-" * 40)
show_logo()

print("\n2. Testing show_disclaimer():")
print("-" * 40)
show_disclaimer()

print("\nDisclaimer test complete!")
