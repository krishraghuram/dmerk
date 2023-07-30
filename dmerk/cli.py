import pathlib
import argparse
import textwrap
import json
import sys

import dmerk.generate as generate
import dmerk.compare as compare
import dmerk.utils as utils


def _generate(args):
    path = pathlib.Path(args.path).resolve()
    merkle = generate.generate(path)
    filename = args.filename
    if not args.no_save:
        utils.save_merkle(path, merkle, filename)
    if args.no_save or args.print:
        utils.dump(merkle, sys.stdout)


def _compare(args):
    matches, unmatched_files_1, unmatched_files_2 = compare.compare(
        utils.generate_or_load(args.path1, args.no_save),
        utils.generate_or_load(args.path2, args.no_save),
    )
    out = {"matches": matches, "unmatched_files": unmatched_files_1 + unmatched_files_2}
    print(json.dumps(utils.path_to_str(out), indent=4))


# TODO
# def _analyse(path):
#     raise NotImplementedError()


def _main(args):
    parser = argparse.ArgumentParser(
        prog="dmerk",
        description="Program to generate, compare and analyse directory merkle trees",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help=textwrap.dedent(
            """
            If specified, the generated merkle tree will not be saved to file.
            This is almost never a good idea, as generating merkle tree is expensive operation, and is worth saving into a file.
            """
        ),
    )
    subparsers = parser.add_subparsers(required=True)

    parser_generate = subparsers.add_parser(
        "generate", description="Generate a merkle tree for a given directory"
    )
    parser_generate.add_argument("path", help="the path to the directory")
    parser_generate.add_argument(
        "-p",
        "--print",
        action="store_true",
        help="if specified, will print the merkle output to stdout",
    )
    parser_generate.add_argument(
        "-f",
        "--filename",
        help="provide a custom filename",
    )
    # # TODO:
    # parser_generate.add_argument("-c", "--compress", help="compress the output file")
    # # Use brotli(11) for compression
    # # Ref: https://www.lucidchart.com/techblog/2019/12/06/json-compression-alternative-binary-formats-and-compression-methods/
    # parser_generate.add_argument("--save-format", help="specify save format")
    # parser_generate.add_argument("--compression-format", help="specify compression format")
    # # What save formats and compression formats to support?
    # # Potential save formats: json, json-like (ion, cbor), pickle etc.
    # # Potential cmp formats: gzip, bzip2, xz, brotli, lzma etc.
    parser_generate.set_defaults(func=_generate)

    parser_compare = subparsers.add_parser(
        "compare",
        description=textwrap.dedent(
            """
            Compare two directory merkle trees and return the diffs and matches.

            path1 and path2 are required, and they are the paths to the directories to compare,
            but they can also be paths to .dmerk files that were created using generate.
            Example: `dmerk -p1=/home/raghuram/Documents -p2=/media/raghuram/BACKUP_DRIVE/Documents`
            Example: `dmerk -p1=Documents_e6eaccb4.dmerk -p2=Documents_b2a7cef7.dmerk`
            
            If provided, subpath1 and subpath2 allows you to compare 2 submerkles within the specified merkles.
            This is useful only when specifying paths to .dmerk files
            Example:
            The following command will load two .dmerk files,
            but compare the "Receipts/Rent" subdirectories within the Documents directory.
            ```
            dmerk \
            -p1=Documents_e6eaccb4.dmerk \
            -p2=Documents_b2a7cef7.dmerk \
            -sp1=Receipts/Rent \
            -sp2=Receipts/Rent
            ```
            """
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser_compare.add_argument("-p1", "--path1", required=True)
    parser_compare.add_argument("-p2", "--path2", required=True)
    parser_compare.add_argument("-sp1", "--subpath1")
    parser_compare.add_argument("-sp2", "--subpath2")
    parser_compare.set_defaults(func=_compare)

    # TODO
    # parser_analyse = subparsers.add_parser(
    #     "analyse", description="Analyse a merkle tree to find copies/duplicates within"
    # )
    # parser_analyse.add_argument("path")
    # parser_analyse.set_defaults(func=_analyse)

    args = parser.parse_args(args)
    args.func(args)


# This runs when invoking cli from installed package (via the pyproject.toml script)
def main():
    _main(sys.argv[1:])


# This runs when dev-testing, when invoked as `python -m dmerk.cli`
if __name__ == "__main__":
    _main(sys.argv[1:])
