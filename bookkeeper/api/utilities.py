from beancount import loader
from beancount.core.data import Entries


# Name of metadata field to be set to indicate that the entry is a likely duplicate.
DUPLICATE_META = "__duplicate__"
# Temporary account used by Sorting later to know which txns to pull out
TODO_ACCOUNT = "Equity:TODO"


def parse_journal(fname: str) -> Entries:
    entries, _errors, _options_map = loader.load_file(fname)
    return entries
