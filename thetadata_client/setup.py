"""
Setup configuration for ThetaData Client Package
"""
from setuptools import setup, find_packages

setup(
    name='thetadata-client',
    version='0.1.0',
    description='ThetaData API Client - CRITICAL: Do not delete',
    author='OptionsLab',
    packages=find_packages(),
    install_requires=[
        'pandas>=1.3.0',
        'numpy>=1.21.0',
        'requests>=2.26.0',
    ],
    python_requires='>=3.8',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Financial and Insurance Industry',
        'Topic :: Office/Business :: Financial :: Investment',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
    ],
    keywords='options trading thetadata api client',
)