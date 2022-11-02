from itertools import chain, groupby
from typing import Any, Dict, Optional, Set, List
from pathlib import Path

import yaml
from flask import Flask, request, render_template
from flask_cors import CORS
from beancount import loader
from beancount.core.data import (
    Entries,
    Transaction,
    Pad,
    Balance,
    Directive,
    Posting,
    Open,
)
from beancount.scripts.format import align_beancount

from .formatting import format_postings, indentation_at
from .serialise import DirectiveForSort, from_dict, to_dict

SUPPORTED_DIRECTIVES = {Transaction}
TODO_ACCOUNT = "Equity:TODO"


def create_app():
    app = Flask(__name__)
    cache = Cache()

    with open("/data/CONFIG.yaml") as f:
        config = yaml.full_load(f)

    # Make sure each API is available from other origins
    CORS(app)

    @app.route("/sort/progress", methods=["GET", "POST"])
    def sort_progress():
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
        return {
            "destination_file": cache.destination_file,
            "main_file": cache.main_file,
            "journal_files": [p.name for p in Path("/data").glob("*.beancount")],
        }

    @app.route("/sort/next", methods=["GET", "POST"])
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
        if cache.accounts is None:
            assert cache.main_file is not None
            all_entries = _parse_journal(str(Path("/data") / cache.main_file))
            cache.accounts = sorted(
                [entry.account for entry in all_entries if _is_open_account(entry)]
            )
        if cache.to_sort is None:
            # Load the journal file
            assert cache.main_file is not None and cache.destination_file is not None
            all_entries = _parse_journal(str(Path("/data") / cache.main_file))
            # Load destination file
            with open(Path("/data") / cache.destination_file, "r") as dest:
                cache.destination_lines = dest.read().splitlines()
            to_sort = [entry for entry in all_entries if _is_sortable(cache, entry)]
            # Rank todos by most promising
            categorised = [
                _auto_categorise(config, str(i), entry)
                for (i, entry) in enumerate(to_sort)
            ]
            cache.to_sort = _rank_order(categorised)
        # find the $max most promising and return that here
        max_txns = request.args.get("max", 20)
        return {
            "to_sort": [to_dict(txn) for txn in cache.to_sort[:max_txns]],
            "accounts": cache.accounts,
        }

    @app.route("/sort/commit", methods=["GET", "POST"])
    def commit_sort():
        """
        POST
        Args: write=True for this to actually write out to the file
        """
        assert (
            cache.destination_lines is not None and cache.destination_file is not None
        )
        with open(Path("/data") / cache.destination_file) as dest:
            before = dest.read()
        dest_output = "\n".join(cache.destination_lines)
        # Run the beancount auto-formatter
        formatted_output = align_beancount(dest_output)
        if request.args.get("write", False):
            assert request.method == "POST"
            with open(Path("/data") / cache.destination_file, mode="w") as dest:
                dest.write(formatted_output)
        return {
            "before": before,
            "after": formatted_output,
        }

    # Needed so that it sees my edits to the template file once this app is running
    app.config["TEMPLATES_AUTO_RELOAD"] = True

    @app.route("/collect.py")
    def collect_script():
        return render_template("collect.py.jinja", name="Zahan")

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


def _is_open_account(entry: Directive) -> bool:
    """
    We include all accounts, including the closed ones, because you never know if
    I'm editing an old transaction.
    """
    return type(entry) is Open


def _auto_categorise(
    config: Dict[str, Any], id: str, entry: Directive
) -> DirectiveForSort:
    for pat, account in config["categories"].items():
        if pat.lower() in entry.payee.lower():
            return DirectiveForSort(id=id, entry=entry, autocat=account)
    return DirectiveForSort(id=id, entry=entry)


def _rank_order(entries: List[DirectiveForSort]) -> List[DirectiveForSort]:
    key_autocat = lambda ent: ent.auto_category or ""
    key_payee = lambda ent: ent.entry.payee
    # order by the auto_category
    entries.sort(key=key_autocat)
    # group by the auto_category, and save it in a list of lists
    groups = [list(txns) for k, txns in groupby(entries, key_autocat)]
    # order list of lists by number of txns (desc)
    groups.sort(key=len, reverse=True)
    # sort by payee within a given category
    for g in groups:
        g.sort(key=key_payee)
    # move the group of txns that have no category to the end
    for i in range(len(groups)):
        if groups[i][0].auto_category is None:
            groups.append(groups.pop(i))
    # flatten
    return list(chain.from_iterable(groups))


class Cache:
    op: Optional[str] = None
    destination_file: Optional[str] = None
    main_file: Optional[str] = None
    to_sort: Optional[List[DirectiveForSort]] = None
    destination_lines: Optional[List[str]] = None
    accounts: Optional[List[str]] = None

    def reset(self):
        self.op = None
        self.destination_file = None
        self.main_file = None
        self.to_sort = None
        self.destination_lines = None
        self.accounts = None


def _is_sortable(cache: Cache, entry: Directive) -> bool:
    assert cache.destination_file is not None
    return (
        type(entry) in SUPPORTED_DIRECTIVES
        and TODO_ACCOUNT in _accounts(entry)
        and Path(entry.meta["filename"]).name == cache.destination_file
    )


def _index_of(items: List[DirectiveForSort], id: str) -> int:
    found = -1
    for i, item in enumerate(items):
        if item.id == id:
            found = i
            break
    if found < 0:
        raise IndexError
    return found


def _replace_todo_with(cache: Cache, drs: DirectiveForSort, replacements: Set[Posting]):
    """
    Replace the todo posting with the $replacements in $destination_lines
    $entry is unchanged, because it will be deleted now
    """
    lineno = None
    for posting in drs.entry.postings:
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
