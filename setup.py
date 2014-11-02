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
        Extension('tonnikala.runtime._buffer', ['tonnikala/runtime/_buffer.c']),
    ]
)

extra_kw = dict(features={'speedups': speedups })

setup(
    name='tonnikala',
    version='0.16',
    description='Python templating engine - the one ton solution',
    author='Antti Haapala',
    author_email='antti@haapala.name',
    url='https://github.com/ztane/Tonnikala',
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Framework :: Pyramid",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.3",
        "Programming Language :: Python :: Implementation :: CPython",
        "Topic :: Text Processing :: Markup",
        "Topic :: Text Processing :: Markup :: HTML"
    ],
    install_requires="""
        six>=1.4.1
        markupsafe>=0.18
    """.split(),
    setup_requires=[],
    include_package_data=True,
    packages=find_packages(),
    test_suite = "tonnikala.tests.test_all",
    tests_require=[],
    **extra_kw
)
