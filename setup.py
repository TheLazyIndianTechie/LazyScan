from setuptools import setup

setup(
    name='lazyscan',
    version='0.2.0',  # Incremented version: 0.1.9 → 0.2.0 (added macOS cache cleaner)
    py_modules=['lazyscan'],
    entry_points={
        'console_scripts': [
            'lazyscan=lazyscan:main',
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
