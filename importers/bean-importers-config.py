#!/usr/bin/env python3
"""Import configuration."""

from itertools import chain
from os import path
import yaml

# import argparse
# parser = argparse.ArgumentParser(description="Collecting beans")
# parser.add_argument('--collect-config', required=True, help='CONFIG.yaml file location')
# parser.add_argument('action', help='download, or the bean-* commands')
# (args, _) = parser.parse_known_args()
# print(args.collect_config)

# load accounts config
# FIXME: hard-coded for now, see beancount issue https://bitbucket.org/blais/beancount/issues/358/
fname = path.join(path.dirname(__file__), "../../accounts/CONFIG.yaml")
with open(fname) as f:
    CONFIGyaml = yaml.full_load(f)

# go through the regular `bean-{identify,extract,file}` flow


# ----- Don't ask. Python modules are the worst -----

from ofxparse import OfxParser
from titlecase import titlecase

from beancount.core.number import D
from beancount.core.amount import Amount
from beancount.core import data
from beancount.ingest import importer

from datetime import timedelta
from io import StringIO
from os import path


class OFXImporter(importer.ImporterProtocol):
    """An importer for Open Financial Exchange files."""

    def __init__(self, account: str, currency: str, account_id: str):
        """
        Create a new importer posting to the given account.
        account_id = account ID that the OFX declares
        """
        self.account = account
        self.currency = currency
        self.account_id = account_id

    def name(self):
        """Include the filing account in the name."""
        return '{}: "{}"'.format(super().name(), self.file_account(None))

    def identify(self, file):
        # Match for a compatible MIME type.
        if file.mimetype() not in {
            "application/x-ofx",
            "application/vnd.intu.qbo",
            "application/vnd.intu.qfx",
        }:
            return False

        # Match the account id.
        ofx = OfxParser.parse(strio(file.contents()))
        return ofx.account.account_id == self.account_id

    def file_account(self, _):
        """Return the account against which we post transactions."""
        return self.account

    def file_date(self, file):
        ofx = OfxParser.parse(strio(file.contents()))
        return ofx.account.statement.end_date

    def extract(self, file, existing_entries=None):
        """Extract a list of partially complete transactions from the file."""
        return extract(file, self.account, self.FLAG, self.currency)


def extract(file, account_name, flag, currency):
    ofx = OfxParser.parse(strio(file.contents()))
    account = ofx.account
    statement = account.statement
    assert statement.currency.lower() == currency.lower(), (
        statement.currency + " != " + currency
    )
    ledger = []
    # create transactions
    for transaction in statement.transactions:
        units = Amount(transaction.amount, currency)
        posting = data.Posting(account_name, units, None, None, None, None)
        ref = data.new_metadata(file.name, 0)
        entry = data.Transaction(
            ref,
            transaction.date.date(),
            flag,
            titlecase(transaction.payee),
            transaction.memo,
            data.EMPTY_SET,
            data.EMPTY_SET,
            [posting],
        )
        ledger.append(entry)
    ledger = data.sorted(ledger)
    # make balance
    b = balance(file, account_name, currency, statement, ledger)
    if b != None:
        ledger.append(b)
    return ledger


def balance(file, account_name, currency, statement, ledger):
    if len(ledger) == 0:
        return None
    # Use the last transaction date as the balance assertion date
    # (because the pending transactions will post in-between)
    date = ledger[-1].date
    # The Balance assertion occurs at the beginning of the date, so move
    # it to the following day.
    date += timedelta(days=1)
    units = Amount(statement.balance, currency)
    ref = data.new_metadata(file.name, 0)
    return data.Balance(ref, date, account_name, units, None, None)


def strio(s):
    return StringIO(s)


# ------

"""
CSV importer.
Mostly a rip off of https://bitbucket.org/blais/beancount/src/tip/beancount/ingest/importers/csv.py
with small modifications. Mostly I needed to add `row_processor` - though I'm not using CSV importing much.
"""

import csv
import datetime
import enum
import io
import collections
from os import path
from typing import Union, Dict, Callable, Optional

import dateutil.parser

from beancount.core import data
from beancount.core.amount import Amount
from beancount.core.number import D
from beancount.core.number import ZERO
from beancount.ingest.importers.csv import Col
from beancount.ingest.importers.mixins import filing
from beancount.ingest.importers.mixins import identifier


def get_amounts(iconfig, row):
    """Get the amount columns of a row.

    Args:
      iconfig: A dict of Col to row index.
      row: A row array containing the values of the given row.
      allow_zero_amounts: Is a transaction with amount D('0.00') okay? If not,
        return (None, None).
    Returns:
      A pair of (debit-amount, credit-amount), both of which are either an
      instance of Decimal or None, or not available.
    """
    debit, credit = None, None
    if Col.AMOUNT in iconfig:
        credit = row[iconfig[Col.AMOUNT]]
    else:
        debit, credit = [
            row[iconfig[col]] if col in iconfig else None
            for col in [Col.AMOUNT_DEBIT, Col.AMOUNT_CREDIT]
        ]

    # If zero amounts aren't allowed, return null value.
    is_zero_amount = (credit is not None and D(credit) == ZERO) and (
        debit is not None and D(debit) == ZERO
    )
    if is_zero_amount:
        return (None, None)

    return (D(debit) if debit else None, D(credit) if credit else None)


class CSVImporter(identifier.IdentifyMixin, filing.FilingMixin):
    """Importer for CSV files."""

    def __init__(
        self,
        item_name: str,
        item_config: dict,
        account_config: dict,
        categorizer: Optional[Callable] = None,
        row_processor: Optional[Callable] = None,
        debug: bool = False,
        **kwds
    ):
        """Constructor.

        Args:
            item_name
            item_config: A dict with the following
                column_map: A dict of Col enum names to the names or indexes of the columns.
                date_format: Special values: "UK"
            account_config: A dict with the following
                account: An account string, the account to post this to.
                currency: A currency string, the currency of this account.
            categorizer: A callable that attaches the other posting (usually expenses)
                to a transaction with only single posting.
            debug: Whether or not to print debug information
        """
        self.item_config = item_config
        self.account_config = account_config

        column_map = self.item_config["column_map"]
        assert isinstance(column_map, dict)
        self.column_map = column_map

        self.account = self.account_config["name"]
        self.currency = self.account_config["currency"]
        content_regexp = self.account_config.get("content_regexp")
        filename_regexp = self.account_config.get("filename_regexp")
        file_prefix = item_name + self.account_config["id"]
        self.debug = debug

        self.categorizer = categorizer
        self.row_processor = row_processor

        # Prepare kwds for filing mixin.
        kwds["filing"] = self.account
        if file_prefix:
            prefix = kwds.get("prefix", None)
            assert prefix is None
            kwds["prefix"] = file_prefix

        # Prepare kwds for identifier mixin.
        matchers = kwds.setdefault("matchers", [])
        matchers.append(("mime", "text/csv"))
        if content_regexp:
            matchers.append(("content", content_regexp))
        if filename_regexp:
            matchers.append(("filename", filename_regexp))

        super().__init__(**kwds)

    def file_date(self, file):
        "Get the maximum date from the file."
        icolumn_map, has_header = normalize_config(self.column_map, file.head())
        if Col.DATE in icolumn_map:
            reader = iter(csv.reader(open(file.name)))
            if has_header:
                next(reader)
            max_date = None
            for row in reader:
                if not row:
                    continue
                if row[0].startswith("#"):
                    continue
                date_str = row[icolumn_map[Col.DATE]]
                date = self.parse_date_liberally(date_str)
                if max_date is None or date > max_date:
                    max_date = date
            return max_date

    def file_account(self, file):
        return self.account

    def extract(self, file, existing_entries=None):
        account = self.file_account(file)
        ledger = []

        # Normalize the configuration to fetch by index.
        icolumn_map, has_header = normalize_config(self.column_map, file.head())

        reader = iter(csv.reader(open(file.name)))

        # Skip header, if one was detected.
        if has_header:
            next(reader)

        def get(row, ftype):
            try:
                return row[icolumn_map[ftype]] if ftype in icolumn_map else None
            except IndexError:  # FIXME: this should not happen
                return None

        # Parse all the transactions.
        first_row = last_row = None
        for index, row in enumerate(reader, 1):
            if not row:
                continue
            if row[0].startswith("#"):
                continue

            # If debugging, print out the rows.
            if self.debug:
                print(row)

            # If provided, provide the row to a custom "processor"
            if isinstance(self.row_processor, collections.abc.Callable):
                row = self.row_processor(row, icolumn_map)
                if self.debug:
                    print("processed: ", row)

            if first_row is None:
                first_row = row
            last_row = row

            # Extract the data we need from the row, based on the configuration.
            date = get(row, Col.DATE)

            payee = get(row, Col.PAYEE)
            if payee:
                payee = payee.strip()

            narration = get(row, Col.NARRATION)

            tag = get(row, Col.TAG)
            tags = {tag} if tag is not None else data.EMPTY_SET

            balance = get(row, Col.BALANCE)

            # Create a transaction
            meta = data.new_metadata(file.name, index)
            if balance is not None:
                meta["balance"] = D(balance)
            date = self.parse_date_liberally(date)
            txn = data.Transaction(
                meta, date, self.FLAG, payee, narration, tags, data.EMPTY_SET, []
            )

            # Attach one posting to the transaction
            amount_debit, amount_credit = get_amounts(icolumn_map, row)

            # Skip empty transactions
            if amount_debit is None and amount_credit is None:
                continue

            for amount in [amount_debit, amount_credit]:
                if amount is None:
                    continue
                units = Amount(amount, self.currency)
                txn.postings.append(
                    data.Posting(account, units, None, None, None, None)
                )

            # Attach the other posting(s) to the transaction.
            if isinstance(self.categorizer, collections.abc.Callable):
                txn = self.categorizer(txn)

            # Add the transaction to the output list
            ledger.append(txn)

        # this has the bug where it mis-sorts within a given day, which is important for the balance
        # ledger = data.sorted(ledger)

        # Figure out if the file is in ascending or descending order.
        first_date = self.parse_date_liberally(get(first_row, Col.DATE))
        last_date = self.parse_date_liberally(get(last_row, Col.DATE))
        is_ascending = first_date < last_date
        # Reverse the list if the file is in descending order
        if not is_ascending:
            ledger = list(reversed(ledger))

        # Add a balance entry if possible
        if Col.BALANCE in icolumn_map and ledger:
            entry = ledger[-1]
            date = entry.date + datetime.timedelta(days=1)
            balance = entry.meta.get("balance", None)
            if balance:
                meta = data.new_metadata(file.name, index)
                ledger.append(
                    data.Balance(
                        meta, date, account, Amount(balance, self.currency), None, None
                    )
                )

        # Remove the 'balance' metadata.
        for entry in ledger:
            entry.meta.pop("balance", None)

        return ledger

    def parse_date_liberally(self, string):
        """Parse arbitrary strings to dates.

        This function is intended to support liberal inputs, so that we can use it
        in accepting user-specified dates on command-line scripts.

        Args:
        string: A string to parse.
        Returns:
        A datetime.date object.
        """
        # Rely on the most excellent dateutil.
        dayfirst = False
        if self.item_config.get("date_format") == "UK":
            dayfirst = True
        return dateutil.parser.parse(string, dayfirst=dayfirst).date()


def normalize_config(config, head):
    """Using the header line, convert the configuration field name lookups to int indexes.

    Args:
      config: A dict of Col types to string or indexes.
      head: A string, some decent number of bytes of the head of the file.
      dialect: A dialect definition to parse the header
    Returns:
      A pair of
        A dict of Col types to integer indexes of the fields, and
        a boolean, true if the file has a header.
    Raises:
      ValueError: If there is no header and the configuration does not consist
        entirely of integer indexes.
    """
    has_header = csv.Sniffer().has_header(head)
    index_config = {}
    if has_header:
        header = next(csv.reader(io.StringIO(head)))
        field_map = {
            field_name.strip(): index for index, field_name in enumerate(header)
        }
        for field_type, field in config.items():
            if isinstance(field, str):
                field = field_map[field]
            index_config[Col[field_type]] = field
    else:
        if any(not isinstance(field, int) for _, field in config.items()):
            raise ValueError(
                "CSV config without header has non-index fields: " "{}".format(config)
            )
        for field_type, field in config.items():
            index_config[Col[field_type]] = field
    return index_config, has_header


# ------


from beancount.ingest import importer


class DummyImporter(importer.ImporterProtocol):
    """An importer that does nothing."""

    def __init__(self, account):
        self.account = account

    def identify(self, file):
        return False

    def file_account(self, _):
        return self.account


# ------


"""Attempt at an importer for PDF statements.
For pay statements, mostly.
"""

import datetime
from os import path
import re
from subprocess import run, DEVNULL
from tempfile import NamedTemporaryFile

from dateutil.parser import parse as parse_datetime

from beancount.ingest import importer


def is_pdftotext_installed():
    """Return true if the external tool is installed."""
    run(["pdftotext", "--help"], check=True, stdout=DEVNULL, stderr=DEVNULL)
    return True


def pdf_to_text(filename):
    """Convert a PDF file to a text equivalent.

    Args:
      filename: A string path, the filename to convert.
    Returns:
      A string, the text contents of the filename.
    """
    assert is_pdftotext_installed(), "You need to install `poppler` for `pdftotext`"
    outfile = NamedTemporaryFile()
    done = run(["pdftotext", filename, outfile.name], capture_output=True, text=True)
    if done.returncode != 0 or done.stderr:
        raise ValueError(done.stderr)
    return outfile.read().decode()


class PDFImporter(importer.ImporterProtocol):
    """An importer for PDF pay statements."""

    def __init__(self, account, content_regexp=None, filing_name=None):
        self.account = account
        self.content_regexp = content_regexp
        self.filing_name = filing_name

    def identify(self, file):
        if file.mimetype() != "application/pdf":
            return False

        # Look for words in the PDF file.
        # The filename they provide isn't useful.
        text = file.convert(pdf_to_text)
        if text and self.content_regexp:
            return re.search(self.content_regexp, text, flags=re.IGNORECASE) is not None

    def file_name(self, _):
        return self.filing_name

    def file_account(self, _):
        return self.account

    def file_date(self, file):
        # Get the actual statement's date from the contents of the file.
        text = file.convert(pdf_to_text)
        return max(
            parse_datetime(match.group(1)).date()
            for match in re.finditer(r"(\d{2}/\d{2}/\d{4})", text)
        )


# ------


def make_importers(item):
    (credentials_name, institution) = item

    def importer(account):
        importer = institution.get("importer")
        if importer == "OFX":
            account_id = account["number"] if "number" in account else account["id"]
            return OFXImporter(account["name"], account["currency"], account_id)
        elif importer == "CSV":
            return CSVImporter(credentials_name, institution, account)
        elif importer == "PDF":
            return PDFImporter(
                account["name"],
                content_regexp=account.get("content_regexp"),
                filing_name=account.get("filing_name"),
            )
        elif importer == "custom":
            return DummyImporter(account["name"])
        else:
            return None

    return [ii for ii in map(importer, institution["accounts"]) if ii is not None]


# the list(..) turns this from an iterable to a materialized list
CONFIG = list(
    # aka, flatten(..)
    chain.from_iterable(map(make_importers, CONFIGyaml["importers"].items()))
)
