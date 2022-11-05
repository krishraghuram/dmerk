# Readme

dmerk (pronounced dee-merk) is a program that creates a [merkle tree](https://en.wikipedia.org/wiki/Merkle_tree) for your directories.

This can be useful in many situations. For example, to detect which file was modified, or to compare two backups for duplicate files.
Think hash digest / checksum verification, but instead of comparing just a pair of hash digests, we are comparing two trees of digests.

## Installation

```
pip install dmerk
```

## Usage / Quickstart

dmerk can be used to generate, compare and analyse directory merkle trees

#### generate

To generate a merkle tree for a directory:
```
dmerk generate /path/to/directory
```

By default, the output is not printed to stdout, since it may be quite large and might pollute the terminal.
Instead, the output is saved as a json file in the current directory.
This behavior can be modified using the `--no-save` and `--print` flags to the `generate` subcommand.

#### compare

To compare two merkle trees,
```
dmerk compare <path1> <path2>
```

The paths path1 and path2 can be paths to directories, or they can be path to json files created using generate.

#### analyse

#### help

To view the help text from the cli (which provides more information than this usage section):

```
dmerk --help
dmerk generate --help
dmerk compare --help
dmerk analyse --help
```

## Features and Limitations

* Currently tested only for Linux, support for Windows and OSX coming soon™.
* The program requires read permission on files, and read and execute permissions on directories. Missing permission would throw an exception.
* Will only handle normal files, directories and symlinks (to normal files and directories).
	- Presence of "special" files like char/block devices, sockets, pipes, or symlinks (to "special" files) will throw an exception.
* Will handle hidden files and directories.
* Will only work for file and directory names that are valid utf-8 byte sequences.
	- If you'd like support for non-utf-8 file/directory names, kindly +1 [this issue](https://github.com/krishraghuram/dmerk/issues/2).
* Currently, the digest algorithm used is md5, because it's fast. CLI option for this coming soon™.
* Currently, directory digest only depends on it's file contents, and is independent of the file names and file metadata (permissions, owner, group, atime, mtime, ctime etc).
	- If you have a need for directory digest that depends on metadata, please open a new issue explaining the use-case.

## Development

If you want to report bugs/issues, or need help troubleshooting, or have an idea for a new feature/improvement,
kindly file and issue in github, and I'll take a look as soon as I can.
Thank you for showing interest in this software 😁.

### Running tests

Tests can be run using,

```
(venv) raghuram@raghuram-PC:~/Workspace/dmerk$ pytest
(venv) raghuram@raghuram-PC:~/Workspace/dmerk$ pytest -s
(venv) raghuram@raghuram-PC:~/Workspace/dmerk$ python -m pytest
(venv) raghuram@raghuram-PC:~/Workspace/dmerk$ python -m pytest -s
```
