# -*- coding: utf-8 -*-
try:
    from setuptools import setup, find_packages
except ImportError:
    from ez_setup import use_setuptools
    use_setuptools()
    from setuptools import setup, find_packages

from setuptools import Extension, Feature

import platform
import sys

speedups = Feature(
    "optional C speed-enhancements",
    standard = True,
    ext_modules = [
        Extension('tonnikala._speedups',       ['tonnikala/_speedups.c']),
    ],
)

speedups3k = Feature(
    "optional C speed-enhancements",
    standard = True,
    ext_modules = [
        Extension('tonnikala.runtime._buffer', ['tonnikala/runtime/_buffer.c']),
        Extension('tonnikala.runtime.noddy', ['tonnikala/runtime/noddy.c']),
    ]
)

if sys.version_info[0] == 2:
    extra_kw = dict(features={'speedups': speedups})
else:
    extra_kw = dict(features={'speedups3k': speedups3k })
    extra_kw = dict(features={'speedups3k': speedups3k })


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
    **extra_kw
)
