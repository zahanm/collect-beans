from beancount import loader
from beancount.parser import printer
from beancount.core.number import D
from beancount.core.amount import Amount
from beancount.core.data import Transaction, Posting

import argparse
import re
from typing import Optional


straight_matches = {
    r"Tartine Bakery": "Expenses:Food:Snacks",
    r"Trader Joe's": "Expenses:Food:Groceries",
}
straight_regexs = dict(
    zip((re.compile(pat) for pat in straight_matches), straight_matches.values())
)


def attempt_categorize(entry) -> Optional[str]:
    for pat, account in straight_regexs.items():
        if pat.search(entry.payee) != None:
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
