"""Fixes the data for American Express
"""
__copyright__ = "Copyright (C) 2016  Martin Blais"

from collections.abc import Callable

from beancount.core.number import D, ZERO
from beancount.ingest.importers import csv

class Processor(Callable):

    def __call__(self, row, iconfig):
        idx = iconfig[csv.Col.AMOUNT]
        amt = D(row[idx])
        if amt != ZERO:
            # correct for the fact that we're flipping the sign semantics
            row[idx] = str(-amt)
        return row
