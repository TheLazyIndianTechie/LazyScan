from setuptools import setup, find_packages
import os

# Read the README file
with open("README_PYPI.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name='lazyscan',
    version='0.3.1',  # Bug fix: Added missing --version argument
    py_modules=['lazyscan'],
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'lazyscan=lazyscan:main',
        ],
    },
    python_requires='>=3.6',
    description='A lazy way to find what\'s eating your disk space - by TheLazyIndianTechie',
    long_description=long_description,
    long_description_content_type="text/markdown",
    author='TheLazyIndianTechie',
    author_email='',  # Add your email if you want
    url='https://github.com/TheLazyIndianTechie/lazyscan',
    project_urls={
        'Bug Tracker': 'https://github.com/TheLazyIndianTechie/lazyscan/issues',
        'Source Code': 'https://github.com/TheLazyIndianTechie/lazyscan',
    },
    classifiers=[
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Topic :: System :: Systems Administration',
        'Topic :: Utilities',
    ],
    keywords='disk space scanner cleaner cache macos terminal cli',
)
