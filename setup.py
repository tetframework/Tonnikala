import os
import sys
from distutils.command.build_ext import build_ext
from distutils.errors import CCompilerError
from distutils.errors import DistutilsExecError
from distutils.errors import DistutilsPlatformError

from setuptools import Distribution as _Distribution, Extension
from setuptools import setup, find_packages
from setuptools.command.test import test as TestCommand

if sys.version_info < (3, 5):
    raise Exception("Tonnikala requires Python 3.5+")

# read in the README file
try:
    with open(os.path.join(os.path.dirname(__file__), "README.rst")) as f:
        README = f.read()
except IOError:
    README = ""

# this is copied from SQLAlchemy; Mike copied it from who knows where
cmdclass = {}

if sys.platform == "win32" and sys.version_info > (2, 6):
    # 2.6's distutils.msvc9compiler can raise an IOError when failing to
    # find the compiler
    # It can also raise ValueError http://bugs.python.org/issue7511
    ext_errors = (
        CCompilerError,
        DistutilsExecError,
        DistutilsPlatformError,
        IOError,
        ValueError,
    )
else:
    ext_errors = (
        CCompilerError,
        DistutilsExecError,
        DistutilsPlatformError,
    )


class BuildFailed(Exception):
    pass


class ve_build_ext(build_ext):
    # This class allows C extension building to fail.

    def run(self):
        try:
            build_ext.run(self)
        except DistutilsPlatformError:
            raise BuildFailed()

    def build_extension(self, ext):
        try:
            build_ext.build_extension(self, ext)
        except ext_errors:
            raise BuildFailed()


cmdclass["build_ext"] = ve_build_ext


class Distribution(_Distribution):
    def has_ext_modules(self):
        # We want to always claim that we have ext_modules. This will be fine
        # if we don't actually have them (such as on PyPy) because nothing
        # will get built, however we don't want to provide an overally broad
        # Wheel package when building a wheel without C support. This will
        # ensure that Wheel knows to treat us as if the build output is
        # platform specific.
        return True


class PyTest(TestCommand):
    # from https://pytest.org/latest/goodpractises.html
    # #integration-with-setuptools-test-commands
    user_options = [("pytest-args=", "a", "Arguments to pass to py.test")]

    default_options = ["-q"]

    def initialize_options(self):
        TestCommand.initialize_options(self)
        self.pytest_args = ""

    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        # import here, cause outside the eggs aren't loaded
        import pytest

        errno = pytest.main(list(self.default_options) + list(self.pytest_args))
        sys.exit(errno)


cmdclass["test"] = PyTest
# blatant SQLALchemy rip-off ends!


# we have an optional speed-up module
speedups = [Extension("tonnikala.runtime._buffer", ["tonnikala/runtime/_buffer.c"])]

features = dict(speedups=speedups)

install_requires = [
    "markupsafe>=0.18",
]

extras_require = {
    "javascript": [
        "slimit3k",
        "ply>=3.4.0",
    ],
}


def do_setup(with_c_extension):
    ext_modules = speedups if with_c_extension else []

    setup(
        name="tonnikala",
        version="1.0.0",
        description="Python templating engine - the one ton solution",
        long_description=README,
        author="Antti Haapala",
        author_email="antti.haapala@interjektio.fi",
        url="https://github.com/tetframework/Tonnikala",
        classifiers=[
            "Development Status :: 4 - Beta",
            "Environment :: Web Environment",
            "Framework :: Pyramid",
            "Intended Audience :: Developers",
            "License :: OSI Approved :: Apache Software License",
            "Operating System :: OS Independent",
            "Programming Language :: Python",
            "Programming Language :: Python :: 3.5",
            "Programming Language :: Python :: 3.6",
            "Programming Language :: Python :: 3.7",
            "Programming Language :: Python :: 3.8",
            "Programming Language :: Python :: 3.9",
            "Programming Language :: Python :: 3.10",
            "Programming Language :: Python :: 3.11",
            "Programming Language :: Python :: 3.12",
            "Programming Language :: Python :: 3.13",
            "Programming Language :: Python :: Implementation :: CPython",
            "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
            "Topic :: Text Processing :: Markup :: HTML",
        ],
        scripts=["bin/tonnikala-compile-jstemplate"],
        install_requires=install_requires,
        extras_require=extras_require,
        setup_requires=[],
        include_package_data=True,
        packages=find_packages(exclude=["tests"]),
        test_suite="tests.test_all",
        tests_require=[
            "pytest",
            "pytest-cov",
        ],
        cmdclass=cmdclass,
        distclass=Distribution,
        ext_modules=ext_modules,
        entry_points="""
        [babel.extractors]
        tonnikala = tonnikala.i18n:extract_tonnikala
        """,
    )


# Disable C extensions for Python 3.14+ due to ABI compatibility issues
if sys.version_info >= (3, 14):
    print("WARNING: Disabling C extensions for Python 3.14+", file=sys.stderr)
    print("Using Python fallback implementation.", file=sys.stderr)
    do_setup(False)
else:
    try:
        do_setup(True)
    except BuildFailed:
        print("WARNING: failed to build the C speed-up extension!", file=sys.stderr)
        print("Proceeding installation without speedups.", file=sys.stderr)
        do_setup(False)
