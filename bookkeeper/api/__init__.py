from typing import Optional, Set, List
from pathlib import Path
from io import StringIO
import textwrap

import yaml
from flask import Flask, request
from beancount import loader
from beancount.core.data import (
    Entries,
    Transaction,
    Pad,
    Balance,
    Directive,
)
from beancount.core.display_context import DisplayContext
from beancount.parser import printer

from .serialise import txn_to_json

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
            # store the submitted categorisations. insert in the right place to in-memory store
            pass
        if cache.all_entries is None:
            # Load the journal file
            assert cache.main_file is not None and cache.destination_file is not None
            cache.all_entries = _parse_journal(str(Path("/data") / cache.main_file))
            with open(Path("/data") / cache.destination_file, "r") as dest:
                cache.destination_lines = dest.read().splitlines()
        # look for all the TODOs, find the $max most promising and return that here
        todos = [entry for entry in cache.all_entries if is_sortable(cache, entry)]
        max_txns = request.args.get("max", 20)
        return {"to_sort": [txn_to_json(txn) for txn in todos[:max_txns]]}

    @app.route("/commit", methods=["POST"])
    def commit():
        """
        Pass ?write=True for this to actually write out to the file
        """
        assert (
            cache.destination_lines is not None and cache.destination_file is not None
        )
        dest_output = "\n".join(cache.destination_lines)
        if request.args.get("write", False):
            with open(cache.destination_file, mode="w") as dest:
                dest.write(dest_output)
        return {"after": dest_output}

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


class Cache:
    op: Optional[str] = None
    destination_file: Optional[str] = None
    main_file: Optional[str] = None
    all_entries: Optional[Entries] = None
    destination_lines: Optional[List[str]] = None

    def reset(self):
        self.op = None
        self.destination_file = None
        self.main_file = None
        self.all_entries = None


def is_sortable(cache: Cache, entry: Directive) -> bool:
    assert cache.destination_file is not None
    return (
        type(entry) in SUPPORTED_DIRECTIVES
        and TODO_ACCOUNT in _accounts(entry)
        and Path(entry.meta["filename"]).name == cache.destination_file
    )
