"""The command line: ``python -m confusable.compat.homoglyphs export DIR``.

It writes the data files that confusable_homoglyphs 3.3.1 reads from the
directory the CONFUSABLE_DATA environment variable names; see ``export`` in
the package.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from confusable.compat.homoglyphs import export


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command line on argv, sys.argv[1:] by default; return the exit status."""
    parser = argparse.ArgumentParser(
        prog="python -m confusable.compat.homoglyphs",
        description="Data files for confusable_homoglyphs 3.3.1, from confusable's "
        "Unicode data.",
    )
    commands = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")
    exporter = commands.add_parser(
        "export",
        help="write categories.json and confusables.json into DIR",
        description="Write categories.json and confusables.json into DIR, laid out "
        "as confusable_homoglyphs 3.3.1 reads them. With the CONFUSABLE_DATA "
        "environment variable naming DIR before the interpreter starts, the "
        "unchanged package loads them instead of its own.",
    )
    exporter.add_argument(
        "directory", metavar="DIR", help="the directory, created if it does not exist"
    )
    args = parser.parse_args(argv)
    for path in export(args.directory):
        print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
