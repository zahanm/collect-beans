from beancount.core.data import Transaction, Posting, Amount

import argparse
from os import path
import re
import shelve
from typing import Optional
import yaml

from lib.utils import print_stderr, pretty_print_stderr


SUPPORTED_DIRECTIVES = {Transaction}
TODO_ACCOUNT = "Equity:TODO"


class Categoriser:
    """
    Categorises transactions using patterns defined in the YAML config file.
    """

    def __init__(self, args: argparse.Namespace):
        with open(args.config) as f:
            CONFIG = yaml.full_load(f)
        assert "categories" in CONFIG, "Need categories to work with"
        self.patterns = {pat.lower(): v for pat, v in CONFIG["categories"].items()}
        self.source = Categoriser._open_shelf(args.source)
        self.destination = Categoriser._open_shelf(args.destination)

    def run(self):
        try:
            # remove anything that was there previously
            self.destination.clear()
            for account, entries in self.source.items():
                print_stderr(f"Processing {account}")
                new_entries = []
                for entry in entries:
                    if type(entry) in SUPPORTED_DIRECTIVES:
                        categorised_account = self.attempt_categorise(entry)
                        if categorised_account:
                            posting = Posting(
                                categorised_account,
                                Amount(None, None),
                                None,
                                None,
                                None,
                                None,
                            )
                            new_postings = entry.postings + [posting]
                        else:
                            new_postings = entry.postings
                        new_entry = Transaction(
                            entry.meta,
                            entry.date,
                            entry.flag,
                            entry.payee,
                            entry.narration,
                            entry.tags,
                            entry.links,
                            new_postings,
                        )
                    else:
                        new_entry = entry
                    new_entries.append(new_entry)
                # this assignment needs to happen just once
                self.destination[account] = new_entries
        finally:
            # close the database
            self.destination.close()
            print_stderr("Categorised written to db file")

    @staticmethod
    def _open_shelf(filename) -> shelve.Shelf:
        return shelve.open(filename)

    def attempt_categorise(self, entry) -> Optional[str]:
        for pat, account in self.patterns.items():
            # TODO: make this into a regex check.
            # It should check word bounds
            if pat in entry.payee.lower():
                return account
        return TODO_ACCOUNT


def _extract_args():
    parser = argparse.ArgumentParser(
        description="Categorise transations. Takes them from $source, categorises them, and writes them to $destination."
    )
    parser.add_argument("config", help="YAML file with categories configured")
    parser.add_argument("source", help="Pickled DB file with postings")
    parser.add_argument("destination", help="Pickled DB file to put postings in")
    parser.add_argument("--debug", action="store_true", help="Debug the steps")
    return parser.parse_args()


if __name__ == "__main__":
    cc = Categoriser(_extract_args())
    cc.run()
