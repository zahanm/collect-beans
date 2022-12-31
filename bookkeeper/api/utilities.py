from typing import Any

from beancount import loader
from beancount.core.data import Entries
import yaml


# Name of metadata field to be set to indicate that the entry is a likely duplicate.
DUPLICATE_META = "__duplicate__"
# Temporary account used by Sorting later to know which txns to pull out
TODO_ACCOUNT = "Equity:TODO"


def parse_journal(fname: str) -> Entries:
    entries, _errors, _options_map = loader.load_file(fname)
    return entries


class Config:

    _data: Any

    def __init__(self) -> None:
        self.reload()

    def reload(self):
        with open("/data/CONFIG.yaml") as f:
            self._data = yaml.full_load(f)

    def __getitem__(self, k: str):
        return self._data[k]
