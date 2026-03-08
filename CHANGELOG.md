# Changelog

# Release 0.3.0 (2025-11-08)

## New Features
* **CLI tab-completion**: Added argcomplete support (requires setup, see README.md)
* **Tooltips**: Added hover tooltips to view full table cell text when truncated
* **Breadcrumb Navigation**: Clickable path segments for quick navigation
* **ClearableInput Widget**: New input widget with one-click clear button (⌫)

## Improvements

### CompareWidget
* Now displays from the root merkle by default
* Added individual Reset button for each widget
* Added sortable columns with visual indicators (▾/▴) and synchronized sorting between widgets
* Improved match display:
    - digest-matches first with solid bg color (3 lines)
    - then name-matches with single-line bg color
    - then unmatched items with bg color that just wraps the text
* Improved column width handling for small terminal windows (digest column now has max width of 32 instead of fixed width)
* Added `_refresh_when_ready` which waits until ready (width is non-zero) and then invokes refresh.
    - Limited it to a max no. of attempts (100) as a safety measure.

### FileManager
* Added filter functionality
* Filter automatically clears when navigating to a new path (only in FileManager)
* Added breadcrumb navigation to header

### UI/UX
* Improved filter inputs with visual feedback (warning colors when filter is active)
* Case-insensitive sorting throughout the UI for more intuitive navigation

### Performance Optimizations
* Improved argcomplete performance through lazy imports for faster startup time

### Code Quality
* Major stylesheet cleanup using nested TCSS styles for better organization and maintainability
* Extracted `fuzzy_match` utility function for consistent filtering behavior
* Refactored filtering logic into reusable utility functions
* Refactored to use Textual utility containers as layout managers for improved readability
* Better type hints throughout (especially for Column sort_key callbacks)
* Increased test coverage (added tests for utils.py)
* Upgraded to Textual 6.4.0

## Bug Fixes
* Fixed crash when rapidly clicking Reset buttons (resolved race conditions between Resize/Unmount and Mount/refresh events)
* Fixed fluidity issues after upgrading to Textual 6.4.0
* Better error handling for invalid Merkle files
* Fixed various minor UI and display issues



# Release 0.2.0 (2025-05-17)

## Major New Features

### Terminal User Interface (TUI)
* **Added comprehensive TUI** built with Textual framework for interactive file management and comparison
* **Generate Tab**: Browse filesystem and generate merkle trees with visual feedback
* **Compare Tab**: Side-by-side comparison of merkle trees with color-coded matches
* **FilePicker Widget**: Navigate and select `.dmerk` files for comparison
* **Favorites Sidebar**: Quick access to frequently used directories
* **Color Hash Visualization**: Visual digest representation using color-coded backgrounds

### Enhanced Merkle Implementation
* **Complete Merkle class rewrite** with improved architecture:
  - Use PurePaths so that we correctly display merkles even when they are not currently present/mounted in the filesystem
  - Lazy loading of children for improved memory efficiency and faster load times
  - Proper JSON serialization/deserialization with `__merkle__` markers
  - Support for symlinks with dedicated Type.SYMLINK
  - Built-in `save()` and `load()` methods with automatic filename generation
  - `traverse()` method for navigating submerkles by path
* **Size tracking**: Added size attribute to all merkle nodes

## CLI Improvements

### Generate Command
* **Major rewrite**: Replaced subprocess-based digest computation (using `md5sum`/`sha256sum`) with pure Python `hashlib.file_digest` to avoid external dependency and improve cross platform support
* Changed default behavior to save output (use `--no-save` to disable)
* Renamed `--continue-on-error` to `--fail-on-error` with inverted logic (continue on error is now default)
* Added proper exit status codes and error handling
* Removed `--print` requirement when using `--no-save`

### Compare Command
* **Complete rewrite** with new shallow comparison algorithm
* New syntax: `dmerk compare -p1 PATH1 -p2 PATH2 [-sp1 SUBPATH1] [-sp2 SUBPATH2]`
* Support for comparing submerkles using subpath arguments
* Cleaner output format with separate `matches`, `unmatched_1`, and `unmatched_2` sections
* Support for comparing both directories and `.dmerk` files

### General CLI
* Added `tui` subcommand to launch the terminal UI
* Added `--no-save` global flag
* Improved help text with examples
* Better error messages and validation

## Architecture & Code Quality

### Project Structure
* Reorganized into proper package structure:
  - `dmerk.generate` - Generation logic (with platform-specific implementations)
  - `dmerk.tui` - Terminal UI components and widgets
  - `dmerk.merkle` - Core Merkle class
  - `dmerk.compare` - Comparison logic
* Added `constants.py` for centralized configuration using platformdirs

### Testing
* Comprehensive test suite with pytest
* Added performance tests and profiling support
* Separate test modules for different platforms (e.g., `test_linux.py`)
* Test markers for slow tests, performance tests, and profiling
* Improved test fixtures and parametrization

### Development Tools
* Added noxfile for automated testing, linting, and formatting
* Git hooks for pre-commit (lint, format, mypy) and pre-push (tests)
* VS Code configuration files for debugging
* Coverage reporting with HTML output

### Documentation
* Comprehensive README rewrite with:
  - Table of contents
  - Detailed usage examples
  - Feature documentation
  - Development setup guide
  - Textual DevTools information

## Technical Improvements

### Performance
* Lazy deserialization of merkle children significantly improves load times
* Optimized digest computation
* Better memory management

### Cross-Platform Support
* Python 3.9 compatibility fixes
* Backport of `hashlib.file_digest` for Python versions < 3.11
* Pure path support for working with paths from different platforms

### Error Handling
* Continue-on-error by default with comprehensive logging
* Better handling of permission errors, broken symlinks, and special files
* Proper cleanup and error messages

## Bug Fixes
* Fixed save location consistency between CLI and TUI
* Fixed issues with non-UTF-8 filenames (documented limitation)
* Fixed metadata change detection to ensure digest stability
* Improved handling of empty directories
* Fixed various edge cases in file traversal

## Breaking Changes
* Changed merkle save format from timestamped JSON to `.dmerk` extension
* Compare output format completely changed (now returns structured dict)
* Renamed CLI flags (`--continue-on-error` → `--fail-on-error` with inverted logic)
* Compare command syntax changed (now requires `-p1`/`-p2` flags)

## Dependencies
* Added textual for TUI functionality
* Added humanize for friendly time formatting
* Added platformdirs for proper app state management
* Development dependencies: textual-dev, nox, flake8, black, mypy, coverage, pytest



# Release 0.1.0 (2023-01-21)

Initial release of dmerk - a command-line tool for creating and comparing directory merkle trees.

## Features

### Core Functionality
* **Merkle Tree Generation**: Create cryptographic merkle trees for directories using MD5 hashing
* **Directory Comparison**: Compare two directory trees to find matches and differences
* **Recursive Hashing**: Efficiently compute digests for entire directory structures

### CLI Commands

#### Generate
* `dmerk generate PATH` - Generate merkle tree for a directory
* Saves output as timestamped JSON file by default
* Options for printing to stdout (`--print`) or skipping save (`--no-save`)
* Custom filename support with `--filename` flag

#### Compare
* `dmerk compare PATH1 PATH2` - Compare two directories or merkle JSON files
* Returns matching files/directories and unmatched items
* Supports comparing live directories or previously generated merkle files
* Deep recursive comparison with parent-child relationship tracking

### File System Support
* Regular files and directories
* Symbolic links (to regular files and directories)
* Hidden files and directories
* Unicode filenames (UTF-8)
* Handles file metadata changes without affecting digest (permissions, timestamps, ownership)

### Design Principles
* **Content-based hashing**: Directory digests depend only on file contents, not names or metadata
* **Stable digests**: Renaming files/directories doesn't change digests
* **Fast comparison**: Leverages merkle tree structure for efficient large-scale comparisons

## Limitations
* Linux only (Windows and macOS support planned)
* Requires read permissions on files and read+execute on directories
* Only handles regular files, directories, and symlinks to them
* Special files (devices, sockets, pipes) will throw exceptions
* Broken symlinks will throw exceptions
* UTF-8 filenames only
* Fixed MD5 digest algorithm (other algorithms planned)

## Technical Details
* JSON-based merkle tree serialization
* Comprehensive test suite using pytest
* Directory digests computed from sorted child digests

## Testing
* Test fixtures for creating filesystem structures
* Special file handling tests (requires sudo for device nodes)
* Permission testing for files and directories
* Metadata change verification tests
* Symlink handling tests
