from itertools import chain, groupby
from shutil import copy
from tempfile import TemporaryDirectory
import textwrap
from typing import Any, Dict, Set, List
from pathlib import Path
from hashlib import sha1
from copy import deepcopy

from flask import Flask, request
from beancount import loader
from beancount.core.data import (
    Entries,
    Transaction,
    Pad,
    Balance,
    Directive,
    Open,
)
from beancount.core.number import D
from beancount.scripts.format import align_beancount
from beancount.ops import validation
from beancount.parser import printer

from .serialise import DirectiveForSort
from .sort_cache import Cache
from .formatting import DISPLAY_CONTEXT, indentation_at
from .serialise import DirectiveForSort, DirectiveMod, mod_from_dict, to_dict

SUPPORTED_DIRECTIVES = {Transaction}
TODO_ACCOUNT = "Equity:TODO"
TAG_SKIP_SORT = "skip-sort"
DELETED_LINE = "\0"
DEFAULT_MAX_TXNS = 20


def create_sort_app(app: Flask, config: Any):
    cache = Cache()

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
        return {
            "destination_file": cache.destination_file,
            "main_file": config["files"]["main-ledger"],
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
        Body (JSON): "sorted"
        Re: "sorted" -- See DirectiveMod. DirectiveMod is a JSON object which includes only the _new_ postings that will replace the equity:todo posting.
        {
            "id": str,
            "type": "replace" | "skip" | "delete"
            "postings": [
                {
                    "account": str,
                    "units": {
                        "number": float,
                        "currency: str
                    }
                },
                ...
            ],
        }
        It can have type "skip" or "delete" too, which are hopefully self-explanatory. No new postings included then.
        Re: "skip", it is a transaction that I don't want to handle right away. We'll set #skip-sort on them.
        """
        if request.method == "POST":
            # store the submitted categorisations. insert in the right place to in-memory store
            assert (
                request.json is not None
                and cache.unsorted is not None
                and cache.destination_lines is not None
            )
            mods = [mod_from_dict(dct) for dct in request.json["sorted"]]
            for mod in mods:
                mod_idx = _index_of(cache.unsorted, mod.id)
                entry = cache.unsorted[mod_idx]
                if mod.type == "replace":
                    assert (
                        mod.postings is not None
                        or mod.payee is not None
                        or mod.narration is not None
                    )
                    _replace_with(cache, entry, mod)
                elif mod.type == "skip":
                    _add_skip_tag(cache, entry)
                elif mod.type == "delete":
                    _delete_transaction(cache, entry)
                # remove sorted item from to_sort and put it in sorted
                cache.sorted.append((cache.unsorted[mod_idx], mod))
                del cache.unsorted[mod_idx]
        if cache.accounts is None:
            all_entries = _parse_journal(
                str(Path("/data") / config["files"]["main-ledger"])
            )
            cache.accounts = sorted(
                [entry.account for entry in all_entries if _is_open_account(entry)]
            )
        if cache.unsorted is None:
            # Load the journal file
            assert cache.destination_file is not None
            all_entries = _parse_journal(
                str(Path("/data") / config["files"]["main-ledger"])
            )
            # Load destination file
            with open(Path("/data") / cache.destination_file, "r") as dest:
                cache.destination_lines = dest.read().splitlines()
            to_sort = [entry for entry in all_entries if _is_sortable(cache, entry)]
            # Rank todos by most promising
            categorised = [
                _auto_categorise(config, str(i), entry)
                for (i, entry) in enumerate(to_sort)
            ]
            cache.unsorted = _rank_order(categorised)
            cache.total = len(cache.unsorted)
        assert cache.total is not None
        # find the $max most promising and return that here
        max_txns = request.args.get("max", DEFAULT_MAX_TXNS)
        return {
            "to_sort": [to_dict(txn) for txn in cache.unsorted[:max_txns]],
            "accounts": cache.accounts,
            "count_total": cache.total,
            "count_sorted": cache.total - len(cache.unsorted),
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
        dest_output = _create_output(cache.destination_lines)
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

    @app.route("/sort/check", methods=["POST"])
    def check_sort():
        """
        Check that bean-check passes on the new file contents.
        It does this by copying the .beancount files to a new temp folder,
        writing out the new contents, and then running bean-check.
        Since that is a write operation (though it doesn't touch the original
        files), this needs to be a POST.
        """
        assert (
            cache.destination_lines is not None and cache.destination_file is not None
        )
        dest_output = _create_output(cache.destination_lines)
        formatted_output = align_beancount(dest_output)

        with TemporaryDirectory() as scratch:
            # copy all the .beancount files to the temp directory
            for f in Path("/data").glob("*.beancount"):
                copy(Path("/data") / f, scratch)
            # override the contents of "dest" with new content
            with open(Path(scratch) / cache.destination_file, "w") as dest:
                dest.write(formatted_output)
            _, errors, _ = loader.load_file(
                Path(scratch) / config["files"]["main-ledger"],
                # Force slow and hardcore validations.
                extra_validations=validation.HARDCORE_VALIDATIONS,
            )

        def hash_error(error):
            h = sha1(error.source["filename"].encode())
            h.update(str(error.source["lineno"]).encode())
            h.update(error.message.encode())
            return h.hexdigest()

        return {
            "check": not errors,
            "errors": {
                hash_error(error): printer.format_error(error) for error in errors
            },
        }

    @app.route("/sort/link")
    def link_sort():
        """
        Searches for a linked Transaction
        """
        assert cache.unsorted is not None
        txn_id = request.args.get("txnID")
        amount = D(request.args.get("amount"))
        assert amount is not None
        amount_abs = amount.copy_abs()
        matching = [
            txn
            for txn in cache.unsorted
            if txn_id != txn.id
            and any(
                [
                    (p.units.number.copy_abs() - amount_abs).copy_abs() < 0.01
                    for p in txn.entry.postings
                ]
            )
        ]
        return {
            "results": [to_dict(txn) for txn in matching],
        }

    @app.route("/sort/sorted", methods=["GET", "POST"])
    def sorted_sort():
        """
        GET
        Returns the transactions that have already been sorted.

        POST
        Remove a sorted transaction and put it back in the "to_sort" list
        """
        if request.method == "POST":
            assert cache.unsorted is not None
            txn_id = request.args.get("txnID")
            idx = next(i for i, (drs, _) in enumerate(cache.sorted) if drs.id == txn_id)
            cache.unsorted.insert(0, cache.sorted[idx][0])
            del cache.sorted[idx]
        max_txns = request.args.get("max", DEFAULT_MAX_TXNS)
        return {
            "sorted": [to_dict(drs) for (drs, _) in cache.sorted[:max_txns]],
            "mods": {mod.id: to_dict(mod) for (_, mod) in cache.sorted[:max_txns]},
        }


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


def _create_output(lines: List[str]) -> str:
    return "\n".join([l for l in lines if l != DELETED_LINE])


def _is_sortable(cache: Cache, entry: Directive) -> bool:
    assert cache.destination_file is not None
    return (
        type(entry) in SUPPORTED_DIRECTIVES
        and TODO_ACCOUNT in _accounts(entry)
        and Path(entry.meta["filename"]).name == cache.destination_file
        and TAG_SKIP_SORT not in entry.tags
    )


def _index_of(items: List[DirectiveForSort], id: str) -> int:
    """
    Will throw a StopIteration if it doesn't find the id
    """
    return next(i for i, item in enumerate(items) if item.id == id)


def _replace_with(cache: Cache, drs: DirectiveForSort, mod: DirectiveMod):
    """
    Replace the todo posting with the $replacements in $destination_lines
    We don't update $entry in cache.to_sort, because it is stored so that we can revert to it
    """
    # We make a copy, because the original is stored later so that we can revert to it
    entry = deepcopy(drs.entry)
    lineno = entry.meta["lineno"]
    # first line + 1 line per posting
    num_lines = 1 + len(entry.postings)
    if mod.postings is not None:
        new_postings = [p for p in entry.postings if p.account != TODO_ACCOUNT]
        new_postings.extend(mod.postings)
        entry = entry._replace(postings=new_postings)
    if mod.payee is not None:
        entry = entry._replace(payee=mod.payee)
    if mod.narration is not None:
        entry = entry._replace(narration=mod.narration)
    # -1 since we're going from line number to position
    replace_pos = lineno - 1
    outs = _format_entry(cache, entry, replace_pos)
    outlines = outs.splitlines()
    if len(outlines) > num_lines:
        outlines[num_lines - 1 :] = ["\n".join(outlines[num_lines - 1 :])]
    assert cache.destination_lines is not None and len(outlines) <= num_lines
    cache.destination_lines[replace_pos : replace_pos + num_lines] = outlines


def _add_skip_tag(cache: Cache, drs: DirectiveForSort):
    # We make a copy, because the original is stored later so that we can revert to it
    entry = deepcopy(drs.entry)
    lineno = entry.meta["lineno"]
    entry = entry._replace(tags=(entry.tags or set()).union({TAG_SKIP_SORT}))
    # -1 since we're going from line number to position
    replace_pos = lineno - 1
    outs = _format_entry(cache, entry, replace_pos)
    assert cache.destination_lines is not None
    # Only want the first line, because that's where the tag will go
    cache.destination_lines[replace_pos] = outs.splitlines()[0]


def _format_entry(cache: Cache, entry: Directive, pos: int):
    assert cache.destination_lines is not None
    indent = indentation_at(cache.destination_lines[pos])
    formatted = printer.format_entry(entry, DISPLAY_CONTEXT)
    return textwrap.indent(formatted, indent)


def _delete_transaction(cache: Cache, drs: DirectiveForSort):
    lineno = drs.entry.meta["lineno"]
    # -1 since we're going from line number to position
    rm_pos = lineno - 1
    # transaction header; postings; newline
    rm_num = 1 + len(drs.entry.postings) + 1
    assert cache.destination_lines is not None
    # note that I cannot just remove these lines because then all subsequent line
    # number lookups from "entry.meta" will be off
    # So I remove these later in _create_output()
    cache.destination_lines[rm_pos : rm_pos + rm_num] = [DELETED_LINE] * rm_num
