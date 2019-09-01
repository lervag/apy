# coding: utf-8
"""Setup script for sintefpy"""

import codecs
from setuptools import setup, find_packages


def readme():
    """Use README as long description"""
    with codecs.open('README.md', encoding='utf-8') as f:
        return f.read()


setup(
    name='apy',
    version='0.1',
    description='CLI script for interacting with local Anki collection',
    long_description=readme(),
    url='https://github.com/lervag/apy',
    author='Karl Yngve Lervåg',
    author_email='karl.yngve@lervag.net',
    classifiers=[
        'Programming Language :: Python :: 3',
    ],
    install_requires=[
        'click',
    ],
    entry_points='''
        [console_scripts]
        apy=apy.cli:main
    ''',
    packages=find_packages(exclude=('tests', 'tests.*')),
    tests_require=['pytest']
)
