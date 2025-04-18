from setuptools import setup

setup(
    name='lazy-space',
    version='0.1.8',  # Incremented version: 0.1.7 → 0.1.8 (renamed module file)
    py_modules=['lazyspace'],
    entry_points={
        'console_scripts': [
            'lazy-space=lazyspace:main',
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
