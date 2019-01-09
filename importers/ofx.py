
from ofxparse import OfxParser
from titlecase import titlecase

from beancount.core.number import D
from beancount.core.amount import Amount
from beancount.core import data
from beancount.ingest import importer

from datetime import timedelta
from io import StringIO
from os import path

class Importer(importer.ImporterProtocol):
    """An importer for Open Financial Exchange files."""

    def __init__(self, account_id, account, currency):
        """Create a new importer posting to the given account."""
        self.account_id = account_id
        self.account = account
        self.currency = currency

    def name(self):
        """Include the filing account in the name."""
        return '{}: "{}"'.format(super().name(), self.file_account(None))

    def identify(self, file):
        # Match for a compatible MIME type.
        if file.mimetype() not in {'application/x-ofx',
                                   'application/vnd.intu.qbo',
                                   'application/vnd.intu.qfx'}:
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
    assert statement.currency.lower() == currency.lower(), statement.currency + ' != ' + currency
    ledger = []
    # create transactions
    for transaction in statement.transactions:
        units = Amount(transaction.amount, currency)
        posting = data.Posting(account_name, units, None, None, None, None)
        ref = data.new_metadata(file.name, 0)
        entry = data.Transaction(ref, transaction.date.date(), flag, titlecase(transaction.payee), transaction.memo,
            data.EMPTY_SET, data.EMPTY_SET, [posting])
        ledger.append(entry)
    ledger = data.sorted(ledger)
    # make balance
    ledger.append(balance(file, account_name, currency, statement, ledger))
    return ledger


def balance(file, account_name, currency, statement, ledger):
    # Use the last transaction date as the balance assertion date
    # (because the pending transactions will post in-between)
    assert len(ledger) > 0
    date = ledger[-1].date
    # The Balance assertion occurs at the beginning of the date, so move
    # it to the following day.
    date += timedelta(days=1)
    units = Amount(statement.balance, currency)
    ref = data.new_metadata(file.name, 0)
    return data.Balance(ref, date, account_name, units, None, None)


def strio(s):
    return StringIO(s)
