#!/bin/bash
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
