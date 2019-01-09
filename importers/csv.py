"""CSV importer. Mostly a rip off of https://bitbucket.org/blais/beancount/src/tip/beancount/ingest/importers/csv.py
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
from beancount.utils.date_utils import parse_date_liberally


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
        debit, credit = [row[iconfig[col]] if col in iconfig else None
                         for col in [Col.AMOUNT_DEBIT, Col.AMOUNT_CREDIT]]

    # If zero amounts aren't allowed, return null value.
    is_zero_amount = ((credit is not None and D(credit) == ZERO) and
                      (debit is not None and D(debit) == ZERO))
    if is_zero_amount:
        return (None, None)

    return (D(debit) if debit else None,
            D(credit) if credit else None)


class Importer(identifier.IdentifyMixin, filing.FilingMixin):
    """Importer for CSV files."""

    def __init__(self, config, account, currency,
                 content_regexp: str=None,
                 filename_regexp: str=None,
                 file_prefix: str=None,
                 categorizer: Optional[Callable]=None,
                 row_processor: Optional[Callable]=None,
                 debug: bool=False,
                 **kwds):
        """Constructor.

        Args:
          config: A dict of Col enum names to the names or indexes of the columns.
          account: An account string, the account to post this to.
          currency: A currency string, the currency of this account.
          categorizer: A callable that attaches the other posting (usually expenses)
            to a transaction with only single posting.
          file_prefix: Naming the file that's put away
          debug: Whether or not to print debug information
        """
        assert isinstance(config, dict)
        self.config = config

        self.account = account
        self.currency = currency
        self.debug = debug

        self.categorizer = categorizer
        self.row_processor = row_processor

        # Prepare kwds for filing mixin.
        kwds['filing'] = account
        if file_prefix:
            prefix = kwds.get('prefix', None)
            assert prefix is None
            kwds['prefix'] = file_prefix

        # Prepare kwds for identifier mixin.
        matchers = kwds.setdefault('matchers', [])
        matchers.append(('mime', 'text/csv'))
        if content_regexp:
            matchers.append(('content', content_regexp))
        if filename_regexp:
            matchers.append(('filename', filename_regexp))

        super().__init__(**kwds)

    def file_date(self, file):
        "Get the maximum date from the file."
        iconfig, has_header = normalize_config(self.config, file.head())
        if Col.DATE in iconfig:
            reader = iter(csv.reader(open(file.name)))
            if has_header:
                next(reader)
            max_date = None
            for row in reader:
                if not row:
                    continue
                if row[0].startswith('#'):
                    continue
                date_str = row[iconfig[Col.DATE]]
                date = parse_date_liberally(date_str)
                if max_date is None or date > max_date:
                    max_date = date
            return max_date

    def file_account(self, file):
        return self.account

    def extract(self, file, existing_entries=None):
        account = self.file_account(file)
        ledger = []

        # Normalize the configuration to fetch by index.
        iconfig, has_header = normalize_config(self.config, file.head())

        reader = iter(csv.reader(open(file.name)))

        # Skip header, if one was detected.
        if has_header:
            next(reader)

        def get(row, ftype):
            try:
                return row[iconfig[ftype]] if ftype in iconfig else None
            except IndexError:  # FIXME: this should not happen
                return None

        # Parse all the transactions.
        first_row = last_row = None
        for index, row in enumerate(reader, 1):
            if not row:
                continue
            if row[0].startswith('#'):
                continue

            # If debugging, print out the rows.
            if self.debug:
                print(row)

            # If provided, provide the row to a custom "processor"
            if isinstance(self.row_processor, collections.abc.Callable):
                row = self.row_processor(row, iconfig)
                if self.debug:
                    print('processed: ', row)

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
                meta['balance'] = D(balance)
            date = parse_date_liberally(date)
            txn = data.Transaction(meta, date, self.FLAG, payee, narration,
                                   tags, data.EMPTY_SET, [])

            # Attach one posting to the transaction
            amount_debit, amount_credit = get_amounts(iconfig, row)

            # Skip empty transactions
            if amount_debit is None and amount_credit is None:
                continue

            for amount in [amount_debit, amount_credit]:
                if amount is None:
                    continue
                units = Amount(amount, self.currency)
                txn.postings.append(
                    data.Posting(account, units, None, None, None, None))

            # Attach the other posting(s) to the transaction.
            if isinstance(self.categorizer, collections.abc.Callable):
                txn = self.categorizer(txn)

            # Add the transaction to the output list
            ledger.append(txn)

        # this has the bug where it mis-sorts within a given day, which is important for the balance
        # ledger = data.sorted(ledger)

        # Figure out if the file is in ascending or descending order.
        first_date = parse_date_liberally(get(first_row, Col.DATE))
        last_date = parse_date_liberally(get(last_row, Col.DATE))
        is_ascending = first_date < last_date
        # Reverse the list if the file is in descending order
        if not is_ascending:
            ledger = list(reversed(ledger))

        # Add a balance entry if possible
        if Col.BALANCE in iconfig and ledger:
            entry = ledger[-1]
            date = entry.date + datetime.timedelta(days=1)
            balance = entry.meta.get('balance', None)
            if balance:
                meta = data.new_metadata(file.name, index)
                ledger.append(
                    data.Balance(meta, date,
                                 account, Amount(balance, self.currency),
                                 None, None))

        # Remove the 'balance' metadta.
        for entry in ledger:
            entry.meta.pop('balance', None)

        return ledger


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
        field_map = {field_name.strip(): index
                     for index, field_name in enumerate(header)}
        for field_type, field in config.items():
            if isinstance(field, str):
                field = field_map[field]
            index_config[Col[field_type]] = field
    else:
        if any(not isinstance(field, int) for _, field in config.items()):
            raise ValueError("CSV config without header has non-index fields: "
                             "{}".format(config))
        for field_type, field in config.items():
            index_config[Col[field_type]] = field
    return index_config, has_header
