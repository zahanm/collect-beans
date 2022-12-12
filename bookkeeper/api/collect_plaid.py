from datetime import date
import json
import logging
from typing import Any, Dict, List

from beancount.core import flags
from beancount.core.number import D
from beancount.core.amount import Amount
from beancount.core import data
from beancount.core.data import Entries, Transaction, Balance, Posting
from plaid import ApiException, Configuration, Environment, ApiClient
from plaid.api.plaid_api import PlaidApi
from plaid.model.account_base import AccountBase
from plaid.model.transaction import Transaction as PlaidTransaction
from plaid.model.transactions_get_request import TransactionsGetRequest
from plaid.model.transactions_get_request_options import TransactionsGetRequestOptions
from plaid.model.transactions_get_response import TransactionsGetResponse

from .serialise import Importer

# Temp account used by Sorting later to know which txns to pull out
TODO_ACCOUNT = "Equity:TODO"


class PlaidCollector:
    client: PlaidApi

    def __init__(self, config: Any) -> None:
        configuration = Configuration(
            host=Environment.Development,
            api_key={
                "clientId": config["plaid"]["client-id"],
                "secret": config["plaid"]["secret"],
                "plaidVersion": "2020-09-14",
            },
        )
        api_client = ApiClient(configuration)
        self.client = PlaidApi(api_client)

    def fetch_transactions(
        self, start: date, end: date, importer: Importer
    ) -> Dict[str, Entries]:
        # the transactions in the response are paginated, so make multiple calls while increasing the offset to
        # retrieve all transactions
        transactions: List[PlaidTransaction] = []
        total_transactions = 1
        first_response = None
        while len(transactions) < total_transactions:
            try:
                opts = TransactionsGetRequestOptions()
                opts.offset = len(transactions)
                req = TransactionsGetRequest(
                    access_token=importer.access_token,
                    start_date=start,
                    end_date=end,
                    options=opts,
                )
                logging.info(
                    f"{importer.name}: %s",
                    json.dumps(req.to_dict(), indent=2, sort_keys=True, default=str),
                )
                response: TransactionsGetResponse = self.client.transactions_get(req)
            except ApiException as e:
                logging.warning("Plaid error: %s", e.body)
                raise e
            transactions.extend(response.transactions)
            if first_response is None:
                first_response = response
                total_transactions = response.total_transactions
            logging.info(
                f"{importer.name}: Fetched {len(response.transactions)} transactions"
            )
            logging.debug(
                "> RAW FETCHED TXNS: %s",
                json.dumps(response.to_dict(), indent=2, sort_keys=True, default=str),
            )

        def construct_ledger(account_meta) -> Entries:
            assert first_response is not None
            # find the matching account in Plaid response
            account: AccountBase = next(
                acc
                for acc in first_response.accounts
                if acc.account_id == account_meta.plaid_id
            )
            if account is None:
                logging.warning("Not present in response: %s", account_meta.name)
                return []
            currency = account_meta.currency
            ledger = []
            for transaction in transactions:
                if account.account_id != transaction.account_id:
                    continue
                assert currency == transaction.iso_currency_code
                if transaction.pending:
                    # we want to wait for the transaction to be posted
                    continue
                amount = D(transaction.amount)
                assert amount is not None
                # sadly, plaid-python parses as `float` https://github.com/plaid/plaid-python/issues/136
                amount = round(amount, 2)
                postings = [
                    Posting(
                        account=account_meta.name,
                        units=Amount(-amount, currency),
                        cost=None,
                        price=None,
                        flag=None,
                        meta=None,
                    ),
                    Posting(
                        account=TODO_ACCOUNT,
                        # In practice, beancount libs are fine with this
                        units=None,  # type: ignore
                        cost=None,
                        price=None,
                        flag=None,
                        meta=None,
                    ),
                ]
                meta = data.new_metadata("foo", 0)
                entry = Transaction._make(
                    [
                        meta,
                        transaction["date"],
                        flags.FLAG_OKAY,
                        transaction["name"],  # payee
                        "",  # narration
                        data.EMPTY_SET,  # tags
                        data.EMPTY_SET,  # links
                        postings,
                    ]
                )
                ledger.append(entry)
            ledger.reverse()  # API returns transactions in reverse chronological order

            # (maybe) add the balance directive
            if end == date.today():
                bal = D(account.balances.current)
                if bal != None:
                    # sadly, plaid-python parses as `float` https://github.com/plaid/plaid-python/issues/136
                    bal = round(bal, 2)
                    meta = data.new_metadata("foo", 0)
                    entry = Balance._make(
                        [
                            meta,
                            end,
                            account_meta.name,
                            Amount(bal, currency),
                            None,  # tolerance
                            None,  # diff_amount
                        ]
                    )
                    ledger.append(entry)

            return ledger

        return {acc.name: construct_ledger(acc) for acc in importer.accounts}
