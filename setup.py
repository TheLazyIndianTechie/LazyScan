from setuptools import setup

setup(
    name='bigfile-map',
    version='0.1.0',
    py_modules=['bigfile_map'],
    entry_points={
        'console_scripts': [
            'bigfile-map=bigfile_map:main',
        ],
    },
    python_requires='>=3.6',
    description='Colorful bar chart of the largest files in a directory tree',
    author='',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
)
