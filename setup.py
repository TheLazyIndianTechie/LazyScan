from setuptools import setup, find_packages

# Read the README file
with open("README_PYPI.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="lazyscan",
    version="0.6.4",
    packages=find_packages(),
    package_data={
        'lazyscan.security': ['default_policy.json'],
    },
    entry_points={
        "console_scripts": [
            "lazyscan=lazyscan.cli.main:cli_main",
        ],
        "lazyscan.plugins": [
            # Plugins will be discovered here automatically
            # Example: 'unity=lazyscan.apps.unity:UnityPlugin',
        ],
    },
    python_requires=">=3.6",
    description="A lazy way to find what's eating your disk space - by TheLazyIndianTechie",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="TheLazyIndianTechie",
    author_email="",  # Add your email if you want
    url="https://github.com/TheLazyIndianTechie/lazyscan",
    project_urls={
        "Bug Tracker": "https://github.com/TheLazyIndianTechie/lazyscan/issues",
        "Source Code": "https://github.com/TheLazyIndianTechie/lazyscan",
    },
    install_requires=[
        "send2trash>=1.8.0",
        "platformdirs>=3.0.0",
        "typer>=0.9.0",
        "orjson>=3.9.0",
        "secretstorage>=3.2.0",
        "cryptography>=41.0.0",
        "humanfriendly>=10.0",
        "sentry-sdk>=1.40.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "hypothesis>=6.0.0",
            "ruff>=0.0.280",
            "black>=23.0.0",
            "mypy>=1.0.0",
            "pre-commit>=3.0.0",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "Topic :: System :: Systems Administration",
        "Topic :: Utilities",
    ],
    keywords="disk space scanner cleaner cache macos terminal cli",
)
