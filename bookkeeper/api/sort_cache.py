from typing import List, Optional

from .serialise import DirectiveForSort, DirectiveMod


class Cache:
    op: Optional[str] = None
    destination_file: Optional[str] = None
    unsorted: Optional[List[DirectiveForSort]] = None
    destination_lines: Optional[List[str]] = None
    accounts: Optional[List[str]] = None
    total: Optional[int] = None
    sorted: List[tuple[DirectiveForSort, DirectiveMod]] = []

    def reset(self):
        self.op = None
        self.destination_file = None
        self.unsorted = None
        self.destination_lines = None
        self.accounts = None
        self.total = None
        self.sorted = []
