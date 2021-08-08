from beancount.core import flags
from beancount.core.number import D
from beancount.core.amount import Amount
from beancount.core import data
from beancount.core.data import Transaction, Balance, Pad, Posting
from beancount.ingest import similar
from beancount.parser import printer
from beancount import loader
import plaid
import yaml

import argparse
from datetime import date, datetime, timedelta
import http.client
import json
import logging
from os import getenv, path
import shelve
import shutil
import subprocess
import sys
import textwrap
from typing import Any, Dict

from lib.utils import print_stderr, pretty_print_stderr


# = Plaid initialisation =
# Get Plaid API keys from https://dashboard.plaid.com/account/keys
PLAID_CLIENT_ID = getenv("PLAID_CLIENT_ID")
PLAID_SECRET = getenv("PLAID_SECRET")
# Use 'sandbox' to test with Plaid's Sandbox environment (username: user_good,
# password: pass_good)
# Use `development` to test with live users and credentials and `production`
# to go live
PLAID_ENV = getenv("PLAID_ENV", "sandbox")
# PLAID_PRODUCTS is a comma-separated list of products to use when initializing
# Link. Note that this list must contain 'assets' in order for the app to be
# able to create and retrieve asset reports.
PLAID_PRODUCTS = getenv("PLAID_PRODUCTS", "transactions")

# PLAID_COUNTRY_CODES is a comma-separated list of countries for which users
# will be able to select institutions from.
PLAID_COUNTRY_CODES = getenv("PLAID_COUNTRY_CODES", "US")

# Name of metadata field to be set to indicate that the entry is a likely duplicate.
DUPLICATE_META = "__duplicate__"

# a dictionary of account => directives that were generated by this script
OUTPUT_FILENAME = "collected_beans_{mode}.db"


class Collector:
    """
    Primary driver
    """

    def __init__(self, args):
        self.args = args
        self.client = plaid.Client(
            client_id=PLAID_CLIENT_ID,
            secret=PLAID_SECRET,
            environment=PLAID_ENV,
            api_version="2020-09-14",
        )
        if args.existing:
            self.existing_entries, _, _ = loader.load_file(self.args.existing)
        else:
            self.existing_entries = None
        self.sync_mode = "balance" if self.args.balance else "transactions"
        self.output_mode = "text" if self.args.txt else "db"
        if self.args.debug:
            logging.getLogger().setLevel(logging.DEBUG)
            http.client.HTTPConnection.debuglevel = 1
            r_log = logging.getLogger("requests.packages.urllib3")
            r_log.setLevel(logging.DEBUG)
            r_log.propagate = True
        else:
            logging.getLogger().setLevel(logging.INFO)
        if self.output_mode == "db":
            self.output = shelve.open(self.output_filename())

    def run(self):
        try:
            with open(self.args.config) as f:
                CONFIG = yaml.full_load(f)
            importers = CONFIG["importers"]

            if any(acc["downloader"] == "plaid" for acc in importers.values()):
                self.check_that_op_is_present()

            # remove anything that was there previously
            self.output.clear()

            # look up and download for each
            for name, item in importers.items():
                if item["downloader"] != "plaid":
                    continue
                logging.info("Item: %s", name)
                assert "accounts" in item
                if self.args.only != None and name != self.args.only:
                    logging.info("%s: skip (not in --only)", name)
                    continue
                if self.sync_mode == "transactions":
                    if not any(
                        acc.get("sync") == "transactions" for acc in item["accounts"]
                    ):
                        logging.info("%s: skip", name)
                        continue
                elif self.sync_mode == "balance":
                    if not any(
                        acc.get("sync") == "balance" for acc in item["accounts"]
                    ):
                        logging.info("%s: skip", name)
                        continue
                if not self.check_institution_status(name, item):
                    logging.info(
                        "%s: unhealthy, skip %s",
                        name,
                        self.get_status_url(item["institution-id"]),
                    )
                    continue
                (_, access_token) = self.fetch_creds_from_op(item)
                logging.info("Got credentials, now talking to bank.")
                if self.sync_mode == "transactions":
                    self.fetch_transactions(name, item, access_token)
                elif self.sync_mode == "balance":
                    self.fetch_balance(name, item, access_token)
        finally:
            if self.output_mode == "db":
                # close the database
                self.output.close()
                print(self.output_filename())

    def fetch_transactions(self, name, item, access_token):
        # Pull transactions for the last 30 days
        start_date = "{:%Y-%m-%d}".format(
            datetime.now() + timedelta(days=-self.args.days)
        )
        end_date = "{:%Y-%m-%d}".format(datetime.now())

        # the transactions in the response are paginated, so make multiple calls while increasing the offset to
        # retrieve all transactions
        transactions = []
        total_transactions = 1
        first_response = None
        while len(transactions) < total_transactions:
            try:
                response = self.client.Transactions.get(
                    access_token, start_date, end_date, offset=len(transactions)
                )
            except plaid.errors.PlaidError as e:
                logging.warning("Plaid error: %s", e.message)
                return
            transactions.extend(response["transactions"])
            if first_response is None:
                first_response = response
                total_transactions = response["total_transactions"]
            if self.args.debug:
                pretty_print_stderr(response)

        if "accounts" not in first_response:
            logging.warning("No accounts, aborting")
            return
        assert "accounts" in item
        for account in item["accounts"]:
            if account["sync"] != "transactions":
                continue
            currency = account["currency"]
            # checking for every configured account in the response
            t_account = next(
                filter(
                    lambda tacc: account["id"] == tacc["account_id"],
                    first_response["accounts"],
                ),
                None,
            )
            if t_account is None:
                logging.warning("Not present in response: %s", account["name"])
                continue
            ledger = []
            for transaction in transactions:
                if account["id"] != transaction["account_id"]:
                    continue
                assert currency == transaction["iso_currency_code"]
                if transaction["pending"]:
                    # we want to wait for the transaction to be posted
                    continue
                amount = D(transaction["amount"])
                # sadly, plaid-python parses as `float` https://github.com/plaid/plaid-python/issues/136
                amount = round(amount, 2)
                posting = Posting(
                    account["name"], Amount(-amount, currency), None, None, None, None
                )
                ref = data.new_metadata("foo", 0)
                entry = Transaction(  # pylint: disable=not-callable
                    meta=ref,
                    date=date.fromisoformat(transaction["date"]),
                    flag=flags.FLAG_OKAY,
                    payee=transaction["name"],
                    narration="",
                    tags=data.EMPTY_SET,
                    links=data.EMPTY_SET,
                    postings=[posting],
                )
                ledger.append(entry)
            ledger.reverse()  # API returns transactions in reverse chronological order
            if self.output_mode == "text":
                # print entries to stdout
                print("; = {}, {} =".format(account["name"], currency))
                print("; {} transactions\n".format(len(ledger)))
            # flag the duplicates
            self.annotate_duplicate_entries(ledger)
            # add the balance directive
            if "current" in t_account["balances"]:
                bal = D(t_account["balances"]["current"])
                # sadly, plaid-python parses as `float` https://github.com/plaid/plaid-python/issues/136
                bal = round(bal, 2)
                if t_account["type"] in {"credit", "loan"}:
                    # the balance is a liability in the case of credit cards, and loans
                    # https://plaid.com/docs/#account-types
                    bal = -bal
                if t_account["balances"]["current"] != None:
                    meta = data.new_metadata("foo", 0)
                    entry = Balance(  # pylint: disable=not-callable
                        meta=meta,
                        date=date.today(),
                        account=account["name"],
                        amount=Amount(bal, currency),
                        tolerance=None,
                        diff_amount=None,
                    )
                    ledger.append(entry)
            if self.output_mode == "db":
                # write the account's ledger to intermediate output, pickled file
                self.output[account["name"]] = ledger
            else:
                assert self.output_mode == "text"
                # print out all the entries
                for entry in ledger:
                    out = printer.format_entry(entry)
                    if DUPLICATE_META in entry.meta:
                        out = textwrap.indent(out, "; ")
                    print(out)

        logging.info("Done %s", name)
        if self.output_mode == "text":
            print()  # newline

    def fetch_balance(self, name, item, access_token):
        try:
            response = self.client.Accounts.get(access_token)
        except plaid.errors.PlaidError as e:
            logging.warning("Plaid error: %s", e.message)
            return
        if self.args.debug:
            pretty_print_stderr(response)

        if "accounts" not in response:
            logging.warning("No accounts, aborting")
            return
        assert "accounts" in item
        for account_def in item["accounts"]:
            if account_def["sync"] != "balance":
                continue
            # checking for every configured account in the response
            account_res = next(
                filter(
                    lambda tacc: account_def["id"] == tacc["account_id"],
                    response["accounts"],
                ),
                None,
            )
            if account_res is None:
                logging.warning("Not present in response: %s", account_def["name"])
                continue
            assert "balances" in account_res
            assert (
                account_def["currency"] == account_res["balances"]["iso_currency_code"]
            )
            if (
                "current" not in account_res["balances"]
                or account_res["balances"]["current"] is None
            ):
                logging.warning("No 'current' account balance, aborting")
                continue
            bal = D(account_res["balances"]["current"])
            # sadly, plaid-python parses as `float` https://github.com/plaid/plaid-python/issues/136
            bal = round(bal, 2)
            if account_res["type"] in {"credit", "loan"}:
                # the balance is a liability in the case of credit cards, and loans
                # https://plaid.com/docs/#account-types
                bal = -bal
            meta = data.new_metadata("foo", 0)
            balance_entry = Balance(  # pylint: disable=not-callable
                meta=meta,
                date=date.today(),
                account=account_def["name"],
                amount=Amount(bal, account_def["currency"]),
                tolerance=None,
                diff_amount=None,
            )
            ledger = []
            ledger.append(self.pad(meta, account_def["name"]))
            ledger.append(balance_entry)
            if self.output_mode == "text":
                print(f"; = {account_def['name']}, {account_def['currency']} =")
                for entry in ledger:
                    out = printer.format_entry(entry)
                    print(out)
            else:
                assert self.output_mode == "db"
                self.output[account_def["name"]] = ledger
        logging.info("Done %s", name)
        if self.output_mode == "text":
            print()  # newline

    def pad(self, meta, account):
        entry = Pad(  # pylint: disable=not-callable
            meta=meta,
            date=date.today() + timedelta(days=-1),
            account=account,
            source_account="Equity:Net-Worth-Sync",
        )
        return entry

    def check_that_op_is_present(self):
        """1Password CLI: https://support.1password.com/command-line/"""
        # check that op is installed, this will throw if not
        subprocess.run(
            ["op", "--version"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def fetch_creds_from_op(self, item):
        """fetch credentials from 1Password"""
        logging.debug("op get item %s", item["op-id"])
        # fetch the item
        ret = subprocess.run(
            ["op", "get", "item", item["op-id"]],
            check=True,
            text=True,
            stdout=subprocess.PIPE,
        )
        item = json.loads(ret.stdout)
        # parse out the item_id and access_token
        item_id, access_token = None, None
        sections = item["details"]["sections"]
        for s in sections:
            if "fields" not in s:
                continue
            if item_id != None and access_token != None:
                break  # short-circuit
            fields = s["fields"]
            for f in fields:
                if f["t"] == "item_id":
                    item_id = f["v"]
                elif f["t"] == "access_token":
                    access_token = f["v"]
        assert item_id != None
        assert access_token != None
        return (item_id, access_token)

    def check_institution_status(self, name, item) -> bool:
        assert self.client
        try:
            # pyre-fixme[16] it doesn't know types for beancount client
            response = self.client.Institutions.get_by_id(
                item["institution-id"], ["US"], _options={"include_status": True}
            )
        except plaid.errors.PlaidError as e:
            logging.warning("Plaid error: %s", e.message)
            return False
        assert "institution" in response
        if "status" in response["institution"]:
            inst_status = response["institution"]["status"]
            logging.debug(inst_status)
            if "transactions_updates" in inst_status:
                if "status" in inst_status["transactions_updates"]:
                    if inst_status["transactions_updates"]["status"] == "DEGRADED":
                        logging.warning(
                            "%s: degraded status, proceeding with fetch", name
                        )
                        return True
                    return inst_status["transactions_updates"]["status"] == "HEALTHY"
        return False

    def get_status_url(self, inst_id: str) -> str:
        return "https://dashboard.plaid.com/activity/status/institution/{}".format(
            inst_id
        )

    def annotate_duplicate_entries(self, new_entries):
        """Flag potentially duplicate entries.
        Args:
        new_entries: A list of lists of imported entries, one for each
            importer.
        Returns:
        Modifies new_entries in-place, potentially with
            modified metadata to indicate those which are duplicated.
        """
        # Find similar entries against the existing ledger only.
        duplicate_pairs = similar.find_similar_entries(
            new_entries, self.existing_entries
        )
        # Add a metadata marker to the extracted entries for duplicates.
        duplicate_set = set(id(entry) for entry, _ in duplicate_pairs)
        for entry in new_entries:
            if id(entry) in duplicate_set:
                entry.meta[DUPLICATE_META] = True

    def output_filename(self):
        return OUTPUT_FILENAME.format(mode=self.sync_mode)


def extract_args():
    parser = argparse.ArgumentParser(
        description=textwrap.dedent(
            """
            Download statements from banks.
            Writes just the file name that the transactions are stored in (in a binary format) to stdout.
            Unless the --txt argument is given, then it prints out the beancount entries directly.
            """
        )
    )
    parser.add_argument("config", help="YAML file with accounts configured")
    parser.add_argument(
        "--existing",
        metavar="BEANCOUNT_FILE",
        default=None,
        help="Beancount file for de-duplication (optional)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=10,
        help="How many days back should the statement go?",
    )
    parser.add_argument(
        "--balance",
        action="store_true",
        help="Run this script in 'balance sync' mode (mutually exclusive with transactions download).",
    )
    parser.add_argument(
        "--txt",
        action="store_true",
        help="Output the beancount entries directly to stdout, instead of writing to a file.",
    )
    parser.add_argument(
        "--debug", action="store_true", help="Debug the request and responses"
    )
    parser.add_argument(
        "--only",
        metavar="IMPORTER_NAME",
        default=None,
        help="Only this importer will be run (optional - useful for debugging)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    collector = Collector(extract_args())
    collector.run()
