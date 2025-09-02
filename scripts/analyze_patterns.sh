#!/bin/bash

# ast-grep usage examples for LazyScan improvement

echo "🔍 Analyzing dangerous file operations..."
echo "======================================="

echo "1. Finding shutil.rmtree calls:"
ast-grep --pattern 'shutil.rmtree($_)' --lang python . || echo "No matches found"

echo -e "\n2. Finding os.remove calls:"
ast-grep --pattern 'os.remove($_)' --lang python . || echo "No matches found"

echo -e "\n3. Finding print statements:"
ast-grep --pattern 'print($_)' --lang python . | wc -l | xargs echo "Total print statements found:"

echo -e "\n4. Finding input calls (potential validation points):"
ast-grep --pattern 'input($_)' --lang python . || echo "No matches found"

echo -e "\n5. Finding glob.glob calls:"
ast-grep --pattern 'glob.glob($_)' --lang python . || echo "No matches found"

echo -e "\n6. Finding try-except blocks:"
ast-grep --pattern 'try: $$$' --lang python lazyscan.py | grep "try:" | wc -l | xargs echo "Try blocks found in main file:"

echo -e "\n📊 Analysis complete! Check the patterns above for improvement opportunities."
