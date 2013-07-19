# -*- coding: utf-8 -*-
try:
    from setuptools import setup, find_packages
except ImportError:
    from ez_setup import use_setuptools
    use_setuptools()
    from setuptools import setup, find_packages

from setuptools import Extension, Feature

import platform

speedups = Feature(
    "optional C speed-enhancements",
    standard = True,
    ext_modules = [
        Extension('tonnikala._speedups', ['tonnikala/_speedups.c']),
        Extension('tonnikala._rope', ['tonnikala/_rope.c']),
    ],
)


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
    test_suite = "tonnikala.tests.test_all",
    tests_require=[],
    features={'speedups': speedups}
)
