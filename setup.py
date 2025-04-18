from setuptools import setup

setup(
    name='lazy-space',
    version='0.1.3',  # Incremented version: 0.1.0 → 0.1.1 (progress display) → 0.1.2 (rebranding) → 0.1.3 (cyberpunk styling)
    py_modules=['bigfile_map'],
    entry_points={
        'console_scripts': [
            'lazy-space=bigfile_map:main',
        ],
    },
    python_requires='>=3.6',
    description='A lazy way to find what\'s eating your disk space - by TheLazyIndianTechie',
    author='TheLazyIndianTechie',
    url='https://github.com/TheLazyIndianTechie/lazy-space',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
)
