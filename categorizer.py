from beancount import loader
from beancount.parser import printer
from beancount.core.number import D
from beancount.core.amount import Amount
from beancount.core.data import Transaction, Posting

import argparse


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
            random = Posting("Equity:Random", None, None, None, None, None)
            new_postings = entry.postings + [random]
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
