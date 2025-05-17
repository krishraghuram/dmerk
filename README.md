# dmerk

[![PyPI version](https://img.shields.io/pypi/v/dmerk.svg)](https://pypi.org/project/dmerk/)
[![License](https://img.shields.io/github/license/krishraghuram/dmerk.svg)](https://github.com/krishraghuram/dmerk/blob/main/LICENSE)

dmerk (pronounced dee-merk) is a program that creates a [merkle tree](https://en.wikipedia.org/wiki/Merkle_tree) for your directories.

This can be useful in many situations. For example, to detect which files were modified, or to compare two backups for duplicate files.
Think hash digest / checksum verification, but instead of comparing just a pair of hash digests, we are comparing two trees of digests.

## Table of Contents
- [Installation](#installation)
- [Usage / Quickstart](#usage--quickstart)
  - [TUI (Terminal User Interface)](#tui-terminal-user-interface)
  - [Generate](#generate)
  - [Compare](#compare)
- [Features and Limitations](#features-and-limitations)
- [Development](#development)

## Installation

```
pip install dmerk
```

## Usage / Quickstart

### TUI (Terminal User Interface)

Launch the TUI for a more interactive experience:

```
dmerk tui
```

The TUI is built with [Textual](https://textual.textualize.io/) and provides a powerful interface for all dmerk functionality. It's especially useful for the `compare` operation, allowing you to quickly navigate and compare different submerkles at various hierarchical levels of two merkle trees, which is more cumbersome with the CLI alone.

### Generate

Generate a merkle tree for a directory:

```
dmerk generate /path/to/directory
```

Options:
- `-p, --print`: Print the merkle output to stdout
- `-f FILENAME, --filename FILENAME`: Provide a custom filename or file path for saving
- `--fail-on-error`: Immediately fail upon encountering errors (such as broken symlinks)
- `--no-save`: If specified, the generated merkle tree will not be saved to file (not recommended as generating merkle trees is computationally expensive)

### Compare

Compare two directory merkle trees and return the diffs and matches:

```
dmerk compare -p1 PATH1 -p2 PATH2 [-sp1 SUBPATH1] [-sp2 SUBPATH2]
```

The paths `PATH1` and `PATH2` are required and can be either:
- Paths to directories to compare
- Paths to `.dmerk` files created using the generate command

Options:
- `--no-save`: If specified, the generated merkle trees will not be saved to file (only applies when comparing directories)

Examples:
```
dmerk compare -p1=/home/raghuram/Documents -p2=/media/raghuram/BACKUP_DRIVE/Documents
dmerk compare -p1=Documents_e6eaccb4.dmerk -p2=Documents_b2a7cef7.dmerk
```

When using `.dmerk` files, you can optionally provide subpaths to compare specific subdirectories:

```
dmerk compare \
-p1=Documents_e6eaccb4.dmerk \
-p2=Documents_b2a7cef7.dmerk \
-sp1=Receipts/Rent \
-sp2=Receipts/Rent
```

This is particularly useful because the compare operation performs a "shallow comparison" that only shows diffs/matches among immediate children.

## Features and Limitations

### Current Support
* Primary testing on Linux; Windows and macOS support coming soon™
* Handles regular files, directories, and symlinks to regular files/directories
* Processes hidden files and directories
* Uses MD5 as the digest algorithm for speed (configurable options planned)

### Requirements
* Read permission for files
* Read and execute permissions for directories
* File and directory names must be valid UTF-8 byte sequences
  - For support of non-UTF-8 filenames, please upvote [this issue](https://github.com/krishraghuram/dmerk/issues/2)

### Limitations
* Does not support special files (character/block devices, sockets, pipes)
* Symlinks to special files will cause exceptions
* Directory digests are currently based only on file contents, not filenames or metadata (permissions, owner, timestamps, etc.)
  - If you need directory digests that include metadata, please open a new issue explaining your use case

## Development

### Contributing
If you want to report bugs, request features, or contribute improvements, please [file an issue on GitHub](https://github.com/krishraghuram/dmerk/issues). I appreciate your interest in this project and will respond as soon as possible 😁.

### Setup
```bash
# Clone and set up the repository
git clone https://github.com/krishraghuram/dmerk.git
cd dmerk
python3 -m venv venv
source venv/bin/activate

# Install development dependencies
pip install -e .[dev]

# Verify installation
dmerk --help
```

### Textual Development Tools
The TUI is built with [Textual](https://textual.textualize.io/). You can use Textual's development tools:

```bash
# Run in dev mode with access to logs and console
textual run --dev dmerk.tui
```

For more information, see the [Textual DevTools documentation](https://textual.textualize.io/guide/devtools/).

### Code Quality

We maintain code quality through automated checks that run as Git hooks:
- Pre-commit: lint, format, and type checking
- Pre-push: unit tests

You can also run these checks manually:

```bash
# Run individual checks
nox --session lint
nox --session format
nox --session mypy
nox --session test
```
