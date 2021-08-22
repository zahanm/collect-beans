import argparse
from typing import List, Set
from io import StringIO
import shelve
import textwrap
from os import path

from beancount import loader
from beancount.core.data import Entries, Directive, Transaction, Balance, Pad
from beancount.core.display_context import DisplayContext
from beancount.parser import printer
from beancount.scripts.format import align_beancount

from collector import DUPLICATE_META
from lib.utils import print_stderr, pretty_print_stderr


SUPPORTED_DIRECTIVES = {Transaction, Balance, Pad}


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
        with open(self.args.journal, mode="r") as journal_file:
            self.journal = journal_file.read()

    def run(self):
        source = self._parse_shelf(self.args.source)
        for account, directives in source.items():
            has_useful_entries = any(
                [type(entry) in SUPPORTED_DIRECTIVES for entry in directives]
            )
            if not has_useful_entries:
                print_stderr(f"Skipping {account}")
                continue
            print_stderr(f"Processing {account}")
            last_balance = self._find_last_balance_entry(account)
            if _is_same_balance_entry(last_balance, directives):
                print_stderr(f"No updates, skipping {account}")
                continue
            lineno = last_balance.meta["lineno"]
            # +1 since we're going from line number to position, and +1 for a newline
            insert_pos = lineno + 1
            print_stderr(f"Insert at -> {insert_pos}")
            destination_lines = self.destination.splitlines()
            destination_lines[insert_pos:insert_pos] = _format_entries(
                directives,
                _indentation_at(destination_lines, lineno),
            ).splitlines()
            self.destination = "\n".join(destination_lines)
            print_stderr(f"Total lines {len(destination_lines)}")
        # run bean-format on the final results
        print_stderr("Formatting")
        self.destination = align_beancount(self.destination)
        print(self.destination)

    def _parse_shelf(self, filename) -> shelve.Shelf:
        # the shelf module doesn't like the suffix, since it adds it automatically
        return shelve.open(filename)

    def _parse_journal_entries(self, journal) -> Entries:
        entries, _errors, _options_map = loader.load_file(journal)
        return entries

    def _parse_entries_from_string(self, journal) -> Entries:
        entries, _errors, _options_map = loader.load_string(journal)
        return entries

    def _find_last_balance_entry(self, account: str) -> Balance:
        """
        Looks for the last "balance" directive for this account in the destination.
        The assumption (which is safe in my journal) is that each account ends its dedicated section with a "balance" entry.
        "destination_entries" itself is a date-ordered list of directives.
        """
        all_entries = self._parse_entries_from_string(self.journal)
        balance_entries = [
            entry
            for entry in all_entries
            if type(entry) is Balance and account in _accounts(entry)
        ]
        if len(balance_entries) == 0:
            # could not find a balance entry for this account
            raise RuntimeError(f"No balance entry for {account}")
        newest_balance = max(
            balance_entries,
            key=lambda entry: entry.date,
        )
        if path.basename(self.args.destination) != path.basename(
            newest_balance.meta["filename"]
        ):
            # make sure that it's in the correct file
            raise RuntimeError(f"Balance entry is not in destination file")
        # it's the last balance entry which the account was found in
        return newest_balance


def _accounts(entry) -> Set[str]:
    if type(entry) is Transaction:
        return set([posting.account for posting in entry.postings])
    if type(entry) in {Pad, Balance}:
        return {entry.account}
    raise RuntimeError(f"Check SUPPORTED_DIRECTIVES before passing a {type(entry)}")


def _is_same_balance_entry(last_balance: Balance, directives: List[Directive]) -> bool:
    if len(directives) != 1 or type(directives[0]) != Balance:
        return False
    balance = directives[0]
    return last_balance.date == balance.date and last_balance.amount == balance.amount


def _indentation_at(lines, lineno) -> str:
    line = lines[lineno - 1]
    num = len(line) - len(line.lstrip())
    return " " * num


DISPLAY_CONTEXT = DisplayContext()
DISPLAY_CONTEXT.set_commas(True)


def _format_entries(entries: Entries, indent: str) -> str:
    outf = StringIO()
    for entry in entries:
        outs = printer.format_entry(entry, DISPLAY_CONTEXT)
        if DUPLICATE_META in entry.meta:
            outs = textwrap.indent(outs, "; ")
        outf.write(textwrap.indent(outs, indent))
        outf.write("\n")  # add a newline
    return outf.getvalue()


def _extract_args():
    parser = argparse.ArgumentParser(
        description="Copies postings from $source and puts them in the right place in $destination. Output on stdout."
    )
    parser.add_argument("config", help="YAML file with accounts configured")
    parser.add_argument("source", help="Pickled DB file to copy postings from")
    parser.add_argument("destination", help="Beancount file to put postings in")
    parser.add_argument("journal", help="main beancount file which includes the others")
    parser.add_argument(
        "--debug", action="store_true", help="Debug the request and responses"
    )
    return parser.parse_args()


if __name__ == "__main__":
    ii = Inserter(_extract_args())
    ii.run()
