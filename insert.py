import argparse
from typing import List
from io import StringIO
import shelve
import sys

from beancount import loader
from beancount.core.data import Entries, Directive, Transaction, Balance, Pad
from beancount.parser import printer


class Inserter:
    """
    Takes a source of entries, and a destination journal, and inserts the postings from the source into the correct locations in destination.
    The source is a pickled db that is a { account => [directives] } map that collector.py outputs.
    """

    def __init__(self, args: argparse.Namespace):
        self.args = args
        # in-memory string to write as the destination file
        with open(self.args.destination, mode="r") as destination_file:
            self.destination = destination_file.read()

    def run(self):
        source = self._parse_shelf(self.args.source)
        for account, directives in source.items():
            has_useful_entries = any(
                [type(entry) in SUPPORTED_DIRECTIVES for entry in directives]
            )
            if not has_useful_entries:
                continue
            insert_lineno = self._find_last_balance_lineno(account) + 1
            destination_lines = self.destination.splitlines()
            destination_lines[insert_lineno:insert_lineno] = _format_entries(
                directives
            ).splitlines()
            self.destination = "\n".join(destination_lines)

    def _parse_shelf(self, filename) -> shelve.Shelf:
        return shelve.open(filename)

    def _parse_journal_entries(self, journal) -> Entries:
        entries, _errors, _options_map = loader.load_file(journal)
        return entries

    def _parse_entries_from_string(self, journal) -> Entries:
        entries, _errors, _options_map = loader.load_string(journal)
        return entries

    def _find_last_balance_lineno(self, account: str):
        """
        Looks for the last "balance" directive for this account in the destination.
        The assumption (which is safe in my journal) is that each account ends its dedicated section with a "balance" entry.
        "destination_entries" itself is a date-ordered list of directives.
        """
        destination_entries = self._parse_entries_from_string(self.destination)
        for entry in reversed(destination_entries):
            if type(entry) is Balance and account in _accounts(entry):
                # it's the first entry after the account was found, use the lineno from the last entry
                return entry.meta["lineno"]
        # could not find a balance entry for this account
        raise RuntimeError(f"No balance entry for {account}")


SUPPORTED_DIRECTIVES = {Transaction, Balance, Pad}


def _accounts(entry):
    if type(entry) is Transaction:
        return set([posting.account for posting in entry.postings])
    if type(entry) in {Pad, Balance}:
        return {entry.account}
    raise RuntimeError(f"Check SUPPORTED_DIRECTIVES before passing a {type(entry)}")


def _format_entries(entries: Entries):
    outf = StringIO()
    printer.print_entries(entries, file=outf)
    return outf.getvalue()


def _extract_args():
    parser = argparse.ArgumentParser(
        description="Copies postings from $source and puts them in the right place in $destination. Output on stdout."
    )
    parser.add_argument("config", help="YAML file with accounts configured")
    parser.add_argument("source", help="Pickled DB file to copy postings from")
    parser.add_argument("destination", help="Beancount file to put postings in")
    parser.add_argument(
        "--debug", action="store_true", help="Debug the request and responses"
    )
    return parser.parse_args()


if __name__ == "__main__":
    ii = Inserter(_extract_args())
    ii.run()
