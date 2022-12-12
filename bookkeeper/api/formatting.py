from io import StringIO
import textwrap
from typing import Set

from beancount.core.display_context import DisplayContext
from beancount.parser import printer
from beancount.core.data import (
    Entries,
    Posting,
)

from .utilities import DUPLICATE_META

DISPLAY_CONTEXT = DisplayContext()
DISPLAY_CONTEXT.set_commas(True)


def format_entries(entries: Entries, indent: str) -> str:
    outf = StringIO()
    for entry in entries:
        outs = printer.format_entry(entry, DISPLAY_CONTEXT)
        if DUPLICATE_META in entry.meta:
            # Make it a comment
            outs = textwrap.indent(outs, "; ")
        outf.write(textwrap.indent(outs, indent))
        outf.write("\n")  # add a newline
    return outf.getvalue()


def format_postings(postings: Set[Posting], indent: str) -> str:
    outl = []
    for posting in postings:
        if posting.units.number is None:
            outs = posting.account
        else:
            # Don't need to get this exactly right because auto-formatter will fix it
            outs = "{}  {:,.2f} {}".format(
                posting.account, posting.units.number, posting.units.currency
            )
        outl.append(textwrap.indent(outs, indent))
    return "\n".join(outl)


def indentation_at(line: str) -> str:
    num = len(line) - len(line.lstrip())
    return " " * num
