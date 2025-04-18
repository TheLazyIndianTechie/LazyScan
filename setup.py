from setuptools import setup

setup(
    name='lazy-space',
    version='0.1.4',  # Incremented version: 0.1.3 → 0.1.4 (animations and humor)
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
