from typing import Dict, List, Optional

from .serialise import DirectiveForSort, DirectiveMod


class Cache:
    op: Optional[str] = None
    destination_file: Optional[str] = None
    unsorted: Optional[List[DirectiveForSort]] = None
    accounts: Optional[List[str]] = None
    total: Optional[int] = None
    sorted: List[DirectiveForSort] = []
    mods: Dict[str, DirectiveMod] = {}  # { mod.id => mod }

    def reset(self):
        self.op = None
        self.destination_file = None
        self.unsorted = None
        self.accounts = None
        self.total = None
        self.sorted = []
        self.mods = {}
