import argparse
from typing import List
from io import StringIO
import sys

from beancount import loader
from beancount.core.data import Entries, Directive, Transaction, Balance, Pad
from beancount.parser import printer


class Inserter:
    """
    Takes source and destination journals, and inserts the postings from the source into the correct locations in destination.
    The usual use is for source to be a temporary file that was used to stage incomplete postings.
    """

    def __init__(self, args: argparse.Namespace):
        self.args = args
        # in-memory string to write as the destination file
        with open(self.args.destination, mode="r") as destination_file:
            self.destination = destination_file.read()

    def run(self):
        source_entries = self._parse_entries_from_file(self.args.source)
        for entry in source_entries:
            if (
                type(entry) is not Transaction
                and type(entry) is not Balance
                and type(entry) is not Pad
            ):
                print(".", end="", file=sys.stderr)
                continue
            print("x", end="", file=sys.stderr)
        # parse source
        # parse destination
        # for each entry in source:
        #   re-parse destination
        #   populate existing entries from old file
        #   look for correct line number to insert
        #   do the insertion
        outf = StringIO()
        printer.print_entries(source_entries, file=outf)
        print(outf.getvalue())

    def _parse_entries_from_file(self, journal) -> Entries:
        entries, _errors, _options_map = loader.load_file(journal)
        return entries

    def _parse_entries_from_string(self, journal) -> Entries:
        entries, _errors, _options_map = loader.load_string(journal)
        return entries

    def _find_lineno(self, entry: Directive):
        """
        Looks for the account in the destination, then gives the last line number before the next section
        """
        destination_entries = self._parse_entries_from_string(self.destination)


def extract_args():
    parser = argparse.ArgumentParser(
        description="Copies postings from $source and puts them in the right place in $destination. Output on stdout."
    )
    parser.add_argument("config", help="YAML file with accounts configured")
    parser.add_argument("source", help="Beancount file to copy postings from")
    parser.add_argument("destination", help="Beancount file to put postings in")
    parser.add_argument(
        "--debug", action="store_true", help="Debug the request and responses"
    )
    return parser.parse_args()


if __name__ == "__main__":
    ii = Inserter(extract_args())
    ii.run()
