import argparse
import sys

def argparser():
    parser = argparse.ArgumentParser(
        description="TODO TODO TODO TODO TODO.",
        epilog="At least one of the parameters (--source or --input) must always be specified.",
        add_help=False,
        usage="%(prog)s [--help] [--source=file] [--input=file]"
    )

    parser.add_argument(
        "--help",
        action="store_true",
        dest="help",
        help="Print a script hint to the standard output (does not load any input).",
    )

    parser.add_argument(
        "--source",
        type=str,
        metavar="file",
        help="Input file with XML representation of the source code. Must be specified in the format --source=file.",
    )

    parser.add_argument(
        "--input",
        type=str,
        metavar="file",
        help="File with inputs for the actual interpretation of the specified source code. Must be specified in the format --input=file.",
    )

    args, unknown = parser.parse_known_args()

    if args.help:
        if len(sys.argv) > 2:
            parser.error("help parameter cannot be combined with any other parameter")
            sys.exit(10)
        parser.print_help()
        sys.exit(0)

    if unknown:
        parser.error(f"Unrecognized arguments: {', '.join(unknown)}")

    if not args.source and not args.input:
        parser.error("At least one of the parameters (--source or --input) must always be specified.")

    return args

def main():
    args = argparser()


if __name__ == "__main__":
    main()