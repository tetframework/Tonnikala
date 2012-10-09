# -*- coding: utf-8 -*-
try:
    from setuptools import setup, find_packages
except ImportError:
    from ez_setup import use_setuptools
    use_setuptools()
    from setuptools import setup, find_packages

import platform

setup(
    name='Tonnikala',
    version='0.12',
    description='',
    author='',
    author_email='',
    #url='',
    install_requires="""
        six
    """.split(),
    setup_requires=[],
    include_package_data=True,
    test_suite='nose.collector',
    tests_require=[]
)
