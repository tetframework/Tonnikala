# Changelog

All notable changes to Tonnikala will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Full support for Python 3.13 and 3.14-dev
- GitHub Actions CI workflow for continuous testing
- Pre-commit configuration for code quality checks
- Automatic detection and adaptation for Python version-specific features

### Changed
- Made slimit (JavaScript support) an optional dependency - install with `[javascript]` extra
- Migrated from deprecated slimit to slimit3k package for JavaScript template support
- Improved error messages for imported templates (AttributeErrors now mention the template name)
- Updated code formatting to use Black throughout the codebase
- Migrated from pkg_resources to importlib.resources for better performance
- Optimized C extension to use PyList_SetSlice for efficient bulk append operations

### Fixed
- Python 3.13+ compatibility: Fixed HTML parser strictness for `<title>` and `<textarea>` elements
  - Python 3.13.6+ follows HTML5 spec more strictly for "escapable raw text mode" elements
  - Override `RCDATA_CONTENT_ELEMENTS` to allow py: control structures in these elements
- Python 3.13+ AST compatibility:
  - Fixed deprecated `starargs`/`kwargs` parameters in ast.Call nodes
  - Fixed deprecated `varargannotation`/`kwargannotation` parameters in ast.arguments
  - Fixed function ordering to ensure block functions are defined before main function
- Python 3.14-dev compatibility: Replaced private C API usage (`_PyList_Extend`) with public API
- Fixed Python 3.10+ code object creation for NoGIL and newer Python versions
- Fixed Python 3.9+ collections.abc imports deprecation warnings
- Fixed line number handling and removed old lnotab mapping
- Fixed Pyramid renderer compatibility issues
- Fixed JavaScript generator star imports and various errors

### Removed
- Dropped support for Python 2.x and Python <= 3.4
- Removed unused TonnikalaXMLParser class (dead code with no tests)

### Security
- Updated dependencies to address security vulnerabilities
- Better handling of template parsing errors

## [1.0.0b5] - 2020-08-28

_Previous releases not documented in this format_
