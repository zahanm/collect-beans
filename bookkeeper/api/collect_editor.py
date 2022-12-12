from io import StringIO
from pathlib import Path
import textwrap
from typing import Any, List

from beancount import loader
from beancount.core.data import Entries, Balance
from beancount.ingest import similar
from beancount.parser import printer
from beancount.scripts.format import align_beancount

from .formatting import DISPLAY_CONTEXT, DUPLICATE_META, format_entries
from .utilities import parse_journal


class LedgerEditor:
    @classmethod
    def insert(cls, config: Any, account: str, new_entries: Entries):
        """
        Note that this is static so that there's no state saved between runs, even accidentally.
        """
        # Parse the existing ledger files
        main_ledger = Path("/data") / config["files"]["main-ledger"]
        existing_entries = parse_journal(str(main_ledger))

        # Flag the duplicates
        cls.annotate_duplicate_entries(new_entries, existing_entries)

        # Read in current file
        current_ledger = Path("/data") / config["files"]["current-ledger"]
        with open(current_ledger, "r") as dest:
            destination_lines = dest.read().splitlines()

        # Find the right insertion point
        lineno = cls.find_insertion_lineno(
            config, account, new_entries, existing_entries, destination_lines
        )
        # -1 since we're going from line number to position, but then +1 for doing this on the next line
        insert_pos = lineno
        destination_lines.insert(
            insert_pos, "\n" + format_entries(new_entries, "").rstrip()
        )

        # Run the beancount auto-formatter
        formatted_output = align_beancount("\n".join(destination_lines))

        # Write it out
        with open(current_ledger, "w") as dest:
            dest.write(formatted_output)

    @classmethod
    def find_insertion_lineno(
        cls,
        config: Any,
        account: str,
        new_entries: Entries,
        existing_entries: Entries,
        destination_lines: List[str],
    ) -> int:
        """
        Looks for the last "balance" directive for this account in the destination.
        The assumption (which is safe in my journal) is that each account ends its dedicated section with a "balance" entry.
        "destination_entries" itself is a date-ordered list of directives.
        """
        matching_balances = [
            entry
            for entry in existing_entries
            if type(entry) is Balance
            and account == entry.account
            and Path(entry.meta["filename"]).name == config["files"]["current-ledger"]
        ]
        if len(matching_balances) == 0:
            # insert at the end of the file
            return len(destination_lines)
        else:
            newest_balance = max(
                matching_balances,
                key=lambda entry: entry.date,
            )
            if len(new_entries) == 1 and newest_balance.date == new_entries[0].date:
                raise RuntimeError(f"No new updates for {account}")
            return newest_balance.meta["lineno"]

    @classmethod
    def annotate_duplicate_entries(cls, new_entries, existing_entries):
        """Flag potentially duplicate entries.
        Args:
        new_entries: A list of lists of imported entries, one for each
            importer.
        Returns:
        Modifies new_entries in-place, potentially with
            modified metadata to indicate those which are duplicated.
        """
        # Find similar entries against the existing ledger only.
        duplicate_pairs = similar.find_similar_entries(new_entries, existing_entries)
        # Add a metadata marker to the extracted entries for duplicates.
        duplicate_set = set(id(entry) for entry, _ in duplicate_pairs)
        for entry in new_entries:
            if id(entry) in duplicate_set:
                entry.meta[DUPLICATE_META] = True
