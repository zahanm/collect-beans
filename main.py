#!/usr/bin/env python3
"""Import configuration."""

# Insert our custom importers path here.
import sys
from os import path
sys.path.insert(0, path.join(path.dirname(__file__)))

from importers import firstpub, amex

from beancount.ingest import extract
from beancount.ingest.importers import csv
from beancount.ingest.scripts_utils import ingest

# Setting this variable provides a list of importer instances.
CONFIG = [
    # FirstPub
    firstpub.Importer({
                    csv.Col.DATE: "Date",
                    csv.Col.AMOUNT_DEBIT: "Debit",
                    csv.Col.AMOUNT_CREDIT: "Credit",
                    csv.Col.PAYEE: "Description"
                },
                "Assets:US:FirstPub:Checking",
                "USD",
                row_processor=firstpub.Processor()),

    # AmEx Gold
    csv.Importer({
                csv.Col.DATE: 0,
                csv.Col.AMOUNT: 7,
                csv.Col.PAYEE: 11},
                "Liabilities:US:AmEx:Gold",
                "USD",
                # regexp to look for in the file content
                [
                    ('filename', 'Transactions.csv')
                ],
                row_processor=amex.Processor())
]

# Override the header on extracted text (if desired).
extract.HEADER = ';; -*- mode: org; mode: beancount; coding: utf-8; -*-\n'

ingest(CONFIG)
