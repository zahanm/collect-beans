from beancount import loader
from beancount.parser import printer
from beancount.core.number import D
from beancount.core.amount import Amount
from beancount.core.data import Transaction, Posting

import argparse
from os import path
import re
from typing import Optional
import yaml


# FIXME: hard-coded for now, see beancount issue https://bitbucket.org/blais/beancount/issues/358/
fname = path.join(path.dirname(__file__), "../accounts/CONFIG.yaml")
with open(fname) as f:
    CONFIG = yaml.load(f)
assert "categories" in CONFIG, "Need categories to work with"
patterns = {pat.lower(): v for pat, v in CONFIG["categories"].items()}


def attempt_categorize(entry) -> Optional[str]:
    for pat, account in patterns.items():
        if pat in entry.payee.lower():
            return account
    # random = Posting("Equity:Random", None, None, None, None, None)
    return None


def main():
    parser = argparse.ArgumentParser(description="Categorize statements")
    parser.add_argument("input", help="The source of transactions to categorize")
    # writes to stdout
    args = parser.parse_args()
    entries, _errors, _options = loader.load_file(args.input)
    for entry in entries:
        if not isinstance(entry, Transaction):
            new_entry = entry
        else:
            account = attempt_categorize(entry)
            if account:
                posting = Posting(account, None, None, None, None, None)
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
        printer.print_entry(new_entry)


if __name__ == "__main__":
    main()
