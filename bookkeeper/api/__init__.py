from typing import Optional, Set, List
from pathlib import Path

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
)

from .formatting import format_postings, indentation_at
from .serialise import DirectiveWithID, from_dict, to_dict

SUPPORTED_DIRECTIVES = {Transaction}
TODO_ACCOUNT = "Equity:TODO"


def create_app():
    app = Flask(__name__)
    cache = Cache()

    with open("/data/CONFIG.yaml") as f:
        config = yaml.full_load(f)

    @app.route("/progress", methods=["GET", "POST"])
    def progress():
        """
        GET
        Call this to init the UI. Gives the various files and accounts info needed.

        POST
        Called when setting the current sorting options. When the destination file and options are chosen.
        Body (form): destination_file, main_file -- both are just the file name
        """
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
            # TODO Also include all "Expense:" accounts here
        }

    @app.route("/next_sort", methods=["GET", "POST"])
    def next_sort():
        """
        GET
        Called to get the first page of entries to sort.
        Args: max -- int for how many entries to return

        POST
        Called when submitting categorisations that have been made, along with returning the next page of entries.
        Body (JSON): sorted -- See DirectiveMod. This is a JSON object which includes only the _new_ postings that will replace the equity:todo posting.
        {
            "id": str,
            "postings": [
                {
                    "account": str,
                    "units": {
                        "number": float,
                        "currency: str
                    }
                },
                ...
            ]
        }
        """
        if request.method == "POST":
            # store the submitted categorisations. insert in the right place to in-memory store
            assert (
                request.json is not None
                and cache.to_sort is not None
                and cache.destination_lines is not None
            )
            mods = [from_dict(dct) for dct in request.json["sorted"]]
            for mod in mods:
                mod_idx = _index_of(cache.to_sort, mod["id"])
                # replace the todo posting
                entry = cache.to_sort[mod_idx]
                _replace_todo_with(cache, entry, mod["postings"])
                # remove sorted item from cache
                del cache.to_sort[mod_idx]
        if cache.to_sort is None:
            # Load the journal file
            assert cache.main_file is not None and cache.destination_file is not None
            all_entries = _parse_journal(str(Path("/data") / cache.main_file))
            # Load destination file
            with open(Path("/data") / cache.destination_file, "r") as dest:
                cache.destination_lines = dest.read().splitlines()
            to_sort = [entry for entry in all_entries if _is_sortable(cache, entry)]
            # TODO Rank TODOs by most promising
            cache.to_sort = [
                DirectiveWithID(id=str(i), entry=entry)
                for (i, entry) in enumerate(to_sort)
            ]
        # find the $max most promising and return that here
        max_txns = request.args.get("max", 20)
        return {"to_sort": [to_dict(txn) for txn in cache.to_sort[:max_txns]]}

    @app.route("/commit", methods=["POST"])
    def commit():
        """
        POST
        Args: write=True for this to actually write out to the file
        """
        assert (
            cache.destination_lines is not None and cache.destination_file is not None
        )
        dest_output = "\n".join(cache.destination_lines)
        # TODO Run the beancount auto-formatter
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


class Cache:
    op: Optional[str] = None
    destination_file: Optional[str] = None
    main_file: Optional[str] = None
    to_sort: Optional[List[DirectiveWithID]] = None
    destination_lines: Optional[List[str]] = None

    def reset(self):
        self.op = None
        self.destination_file = None
        self.main_file = None
        self.to_sort = None
        self.destination_lines = None


def _is_sortable(cache: Cache, entry: Directive) -> bool:
    assert cache.destination_file is not None
    return (
        type(entry) in SUPPORTED_DIRECTIVES
        and TODO_ACCOUNT in _accounts(entry)
        and Path(entry.meta["filename"]).name == cache.destination_file
    )


def _index_of(items: List[DirectiveWithID], id: str) -> int:
    found = -1
    for i, item in enumerate(items):
        if item.id == id:
            found = i
            break
    if found < 0:
        raise IndexError
    return found


def _replace_todo_with(cache: Cache, entry: Directive, replacements: Set[Posting]):
    """
    Replace the todo posting with the $replacements in $destination_lines
    $entry is unchanged, because it will be deleted now
    """
    lineno = None
    for posting in entry.postings:
        if posting.account == TODO_ACCOUNT:
            lineno = posting.meta["lineno"]
            break
    assert lineno is not None
    # -1 since we're going from line number to position
    replace_pos = lineno - 1
    assert cache.destination_lines is not None
    indent = indentation_at(cache.destination_lines[replace_pos])
    formatted = format_postings(replacements, indent)
    cache.destination_lines[replace_pos] = formatted
