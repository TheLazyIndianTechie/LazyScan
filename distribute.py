#!/usr/bin/env python3
"""
Distribution helper for lazyscan
Creates necessary files for distribution
"""

import os


def create_pypi_files():
    """Create files needed for PyPI distribution"""

    # Create MANIFEST.in
    with open("MANIFEST.in", "w") as f:
        f.write("include README.md\n")
        f.write("include LICENSE\n")

    # Create .gitignore if it doesn't exist
    if not os.path.exists(".gitignore"):
        with open(".gitignore", "w") as f:
            f.write(
                """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db
"""
            )


def create_license():
    """Create MIT License file"""
    with open("LICENSE", "w") as f:
        f.write(
            """MIT License

Copyright (c) 2024 TheLazyIndianTechie

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
        )


def create_release_script():
    """Create a script for easy releases"""
    with open("release.sh", "w") as f:
        f.write(
            """#!/bin/bash
# Release script for lazyscan

echo "🚀 Preparing lazyscan for release..."

# Clean previous builds
rm -rf dist/ build/ *.egg-info

# Build distribution
python3 setup.py sdist bdist_wheel

echo "✅ Build complete!"
echo ""
echo "To upload to PyPI:"
echo "  pip install twine"
echo "  twine upload dist/*"
echo ""
echo "To test locally:"
echo "  pip install dist/lazyscan-*.whl"
"""
        )

    os.chmod("release.sh", 0o755)


def main():
    """Run all distribution preparation steps"""
    print("🛠️  Preparing lazyscan for distribution...")

    create_pypi_files()
    print("✅ Created PyPI files")

    create_license()
    print("✅ Created LICENSE file")

    create_release_script()
    print("✅ Created release script")

    print("\n📦 Distribution preparation complete!")
    print("\nNext steps:")
    print("1. Update setup.py with your GitHub URL")
    print("2. Commit all changes to git")
    print("3. Create a GitHub repository")
    print("4. Push to GitHub")
    print("5. Optional: Upload to PyPI with ./release.sh")


if __name__ == "__main__":
    main()
