import pathlib
import argparse
import textwrap
import json
import sys

import dmerk.dmerk as dmerk
import dmerk.compare as compare
import dmerk.utils as utils

parser = argparse.ArgumentParser(prog="dmerk", description="Program to generate, compare and analyse directory merkle trees")
subparsers = parser.add_subparsers(required=True)

def _generate(args):
    path = pathlib.Path(args.path).resolve()
    merkle = dmerk.get_merkle_tree(path)
    filename = args.filename
    if not args.no_save:
        utils.save_merkle(path, merkle, filename)
    if args.no_save or args.print:
        print(utils.dumps(merkle))

def _compare(args):
    matches, unmatched_files_1, unmatched_files_2 = compare.compare(
        utils.generate_or_load(args.path1, args.no_save),
        utils.generate_or_load(args.path2, args.no_save)
    )
    out = {
        "matches": matches,
        "unmatched_files": unmatched_files_1 + unmatched_files_2
    }
    print(json.dumps(utils.path_to_str(out), indent=4))

def _analyse(path):
    # TODO
    raise NotImplementedError()

def _main(args):
    parser = argparse.ArgumentParser(prog="dmerk", description="Program to generate, compare and analyse directory merkle trees")
    subparsers = parser.add_subparsers(required=True)

    parser_generate = subparsers.add_parser("generate", description="Generate a merkle tree for a given directory")
    parser_generate.add_argument("path", help="the path to the directory")
    parser_generate.add_argument("-n", "--no-save", action="store_true", help="if specified, the merkle output will not be saved to file")
    parser_generate.add_argument("-p", "--print", action="store_true", help="if specified, will print the merkle output to stdout")
    parser_generate.add_argument("-f", "--filename", help="default filename will include current datetime and the directory path. this option allows saving to a different filename.")
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
        description=textwrap.dedent("""
            Compare two directory merkle trees and return the diffs and matches.
            path1 and path2 are the paths to the directories,
            but they can also be paths to json files that were created using generate.
        """),
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser_compare.add_argument("path1")
    parser_compare.add_argument("path2")
    parser_compare.add_argument("-n", "--no-save", action="store_true", help="this option is same as no-save in generate, and is applicable only when path1 or path2 are paths to directories")
    parser_compare.set_defaults(func=_compare)

    parser_analyse = subparsers.add_parser("analyse", description="Analyse a merkle tree to find copies/duplicates within")
    parser_analyse.add_argument("path")
    parser_analyse.set_defaults(func=_analyse)
    
    args = parser.parse_args(args)
    args.func(args)

# This runs when invoking cli from installed package (via the setuptools console script)
def main():
    _main(sys.argv[1:])

# This runs during tests
if __name__=="__main__":
    _main(sys.argv[1:])