from beancount import loader
from beancount.parser import printer
from beancount.core.number import D
from beancount.core.amount import Amount
from beancount.core.data import Transaction, Posting

import argparse
import re
from typing import Optional


straight_matches = {
    # food:snacks
    r"Tartine Bakery": "Expenses:Food:Snacks",
    r"Bi-Rite Creamery": "Expenses:Food:Snacks",
    r"ARIZMENDI BAKERY": "Expenses:Food:Snacks",
    r"REVEILLE COFFEE CO": "Expenses:Food:Snacks",
    r"SCHUBERT'S BAKERY": "Expenses:Food:Snacks",
    r"CKE\*B.PATISSERIE": "Expenses:Food:Snacks",
    r"Andersen - Fox Plaza": "Expenses:Food:Snacks",
    # food:groceries
    r"Trader Joe's": "Expenses:Food:Groceries",
    r"Bi-Rite Market": "Expenses:Food:Groceries",
    r"Safeway Store": "Expenses:Food:Groceries",
    r"Wholefds\W": "Expenses:Food:Groceries",
    r"Jai Ho Indian Grocer": "Expenses:Food:Groceries",
    # food:restaurant
    r"Taro\W": "Expenses:Food:Restaurant",
    r"Tst\* Kasa": "Expenses:Food:Restaurant",
    # entertainment
    r"Moviepass": "Expenses:Entertainment:Movies",
    r"NETFLIX\.COM": "Expenses:Entertainment:Movies",
    # shopping:online
    r"Amazon Mktplace": "Expenses:Shopping:Online",
    r"Amzn Mktp US": "Expenses:Shopping:Online",
    r"AMAZON\.COM AMZN.COM/BILL": "Expenses:Shopping:Online",
    r"J CREW\.COM": "Expenses:Shopping:Online",
    r"ZARA\.COM": "Expenses:Shopping:Online",
    r"ABERCROMBIE\.COM": "Expenses:Shopping:Online",
    r"ANTHROPOLOGIE\.COM": "Expenses:Shopping:Online",
    r"Old Navy On-Line": "Expenses:Shopping:Online",
    r"Mangous New York": "Expenses:Shopping:Online",  # ie, this is "Mango, US, New York"
    # shopping:instore
    r"J Crew\W": "Expenses:Shopping:InStore",
    r"J\. Crew\W": "Expenses:Shopping:InStore",
    r"Abercrombie & Fitch": "Expenses:Shopping:InStore",
    r"Uniqlo Union Square": "Expenses:Shopping:InStore",
    r"Urban Outfitters": "Expenses:Shopping:InStore",
    r"Anthropologie San": "Expenses:Shopping:InStore",
    r"H&m San Francisco": "Expenses:Shopping:InStore",
    # shopping:virtual
    r"WWW\.ITUNES\.COM/BILL": "Expenses:Shopping:VirtualGoods",
    # other
    r"At&t Recurr Bill": "Expenses:Home:Internet",
    r"Lyft \*Ride": "Expenses:Transport:Taxi",
    r"Uber \*": "Expenses:Transport:Taxi",
    r"\Wjumpbikeshar\W": "Expenses:Transport:Other",
    r"Autopay Payment": "Liabilities:AccountsPayable",
}
straight_regexs = dict(
    zip(
        (re.compile(pat, flags=re.IGNORECASE) for pat in straight_matches),
        straight_matches.values(),
    )
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
