from decimal import Decimal
from typing import Optional, Set, TypedDict, List
from pathlib import Path
from io import StringIO
import textwrap
import datetime

import yaml
from flask import Flask, request
from beancount import loader
from beancount.core.data import (
    Entries,
    Transaction,
    Pad,
    Balance,
    Directive,
    Posting,
    Amount,
)
from beancount.core.display_context import DisplayContext
from beancount.parser import printer

SUPPORTED_DIRECTIVES = {Transaction}
TODO_ACCOUNT = "Equity:TODO"


def create_app():
    app = Flask(__name__)
    cache = Cache()

    with open("/data/CONFIG.yaml") as f:
        config = yaml.full_load(f)

    @app.route("/progress", methods=["GET", "POST"])
    def progress():
        if request.method == "POST":
            cache.reset()
            cache.op = "sort"
            cache.destination_file = request.form.get("destination_file")
            cache.main_file = request.form.get("main_file")
        data = Path("/data")
        return {
            "destination_file": cache.destination_file,
            "main_file": cache.main_file,
            "journal_files": [p.name for p in data.glob("*.beancount")],
        }

    @app.route("/next_sort", methods=["GET", "POST"])
    def next_sort():
        if request.method == "POST":
            # store the submitted categorisations in-memory
            pass
        # Load the journal file, look for all the TODOs, find the $max most promising and return that here
        assert cache.main_file is not None
        entries = _parse_journal(str(Path("/data") / cache.main_file))
        todos = [entry for entry in entries if is_sortable(cache, entry)]
        max_txns = request.args.get("max", 20)
        return [_txn_to_json(txn) for txn in todos[:max_txns]]
        # return _format_entries(todos[:max_txns], "")

    return app


def _parse_journal(fname: str) -> Entries:
    entries, _errors, _options_map = loader.load_file(fname)
    return entries


def _accounts(entry: Directive) -> Set[str]:
    if type(entry) is Transaction:
        return set([posting.account for posting in entry.postings])
    if type(entry) in {Pad, Balance}:
        return {entry.account}
    raise RuntimeError(f"Check SUPPORTED_DIRECTIVES before passing a {type(entry)}")


DISPLAY_CONTEXT = DisplayContext()
DISPLAY_CONTEXT.set_commas(True)


def _format_entries(entries: Entries, indent: str) -> str:
    outf = StringIO()
    for entry in entries:
        outs = printer.format_entry(entry, DISPLAY_CONTEXT)
        outf.write(textwrap.indent(outs, indent))
        outf.write("\n")  # add a newline
    return outf.getvalue()


class AmountJSON(TypedDict):
    number: Optional[Decimal]
    currency: str


class PostingJSON(TypedDict):
    account: str
    units: AmountJSON


class DirectiveJSON(TypedDict):
    date: datetime.date
    filename: str
    lineno: int
    payee: str
    narration: str
    postings: List[PostingJSON]


def _amount_to_json(amt: Amount) -> AmountJSON:
    return {
        "number": amt.number,
        "currency": amt.currency,
    }


def _posting_to_json(posting: Posting) -> PostingJSON:
    return {
        "account": posting.account,
        "units": _amount_to_json(posting.units),
    }


def _txn_to_json(entry: Directive) -> DirectiveJSON:
    return {
        "date": entry.date,
        "filename": entry.meta["filename"],
        "lineno": entry.meta["lineno"],
        "payee": entry.payee,
        "narration": entry.narration,
        "postings": [_posting_to_json(p) for p in entry.postings],
    }


class Cache:
    op: Optional[str] = None
    destination_file: Optional[str] = None
    main_file: Optional[str] = None

    def reset(self):
        self.op = None
        self.destination_file = None
        self.main_file = None


def is_sortable(cache: Cache, entry: Directive) -> bool:
    assert cache.destination_file is not None
    return (
        type(entry) in SUPPORTED_DIRECTIVES
        and TODO_ACCOUNT in _accounts(entry)
        and Path(entry.meta["filename"]).name == cache.destination_file
    )
