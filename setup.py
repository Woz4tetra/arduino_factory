from setuptools import setup, find_packages

setup(
    name='arduino_factory',
    version='0.0dev',
    packages=find_packages(),
    license='Creative Commons Attribution-Noncommercial-Share Alike license',
    long_description=open('readme.md').read(),
    install_requires=[
        'pyserial',
    ]
)
