"""Fixes the data for First Republic.
"""
__copyright__ = "Copyright (C) 2016  Martin Blais"

from collections.abc import Callable

from beancount.core.number import D, ZERO
from beancount.ingest.importers import csv

class Processor(Callable):

    def __call__(self, row, iconfig):
        idx = iconfig[csv.Col.AMOUNT_DEBIT]
        amt = D(row[idx])
        if amt != ZERO:
            # correct for the fact that they log debits as negative
            row[idx] = str(-amt)
        return row

class Importer(csv.Importer):

    def __init__(self, *args, **kwargs):
        matchers = kwargs.setdefault("matchers", [])
        matchers.append(("filename", r"AccountHistory\.csv"))
        super().__init__(*args, **kwargs)
