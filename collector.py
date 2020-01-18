from beancount.core import flags
from beancount.core.number import D
from beancount.core.amount import Amount
from beancount.core import data
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
import shutil
import subprocess
import sys
import textwrap
from typing import Any, Dict


# = Plaid initialisation =
# Get Plaid API keys from https://dashboard.plaid.com/account/keys
PLAID_CLIENT_ID = getenv("PLAID_CLIENT_ID")
PLAID_SECRET = getenv("PLAID_SECRET")
PLAID_PUBLIC_KEY = getenv("PLAID_PUBLIC_KEY")
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

args = None
client = None
existing_entries = None
sync_mode = None


def run():
    parser = argparse.ArgumentParser(description="Download statements from banks")
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
        help="Run this script in 'balance sync' mode (mutually exclusive with transactions download)",
    )
    parser.add_argument(
        "--debug", action="store_true", help="Debug the request and responses"
    )
    global args
    args = parser.parse_args()

    with open(args.config) as f:
        CONFIG = yaml.full_load(f)
    importers = CONFIG["importers"]

    if args.existing:
        global existing_entries
        existing_entries, _, _ = loader.load_file(args.existing)

    global client
    client = plaid.Client(
        client_id=PLAID_CLIENT_ID,
        secret=PLAID_SECRET,
        public_key=PLAID_PUBLIC_KEY,
        environment=PLAID_ENV,
        api_version="2019-05-29",
    )

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        http.client.HTTPConnection.debuglevel = 1
        r_log = logging.getLogger("requests.packages.urllib3")
        r_log.setLevel(logging.DEBUG)
        r_log.propagate = True
    else:
        logging.getLogger().setLevel(logging.INFO)

    if any(acc["downloader"] == "plaid" for acc in importers.values()):
        check_that_op_is_present()

    global sync_mode
    sync_mode = "balance" if args.balance else "transactions"

    # look up and download for each
    for name, item in importers.items():
        if item["downloader"] != "plaid":
            continue
        logging.info("Item: %s", name)
        (_, access_token) = fetch_creds_from_op(item)
        logging.info("Got credentials, now talking to bank.")
        if sync_mode == "transactions":
            fetch_transactions(name, item, access_token)
        elif sync_mode == "balance":
            fetch_balance(name, item, access_token)


def fetch_transactions(name, item, access_token):
    # Pull transactions for the last 30 days
    start_date = "{:%Y-%m-%d}".format(datetime.now() + timedelta(days=-args.days))
    end_date = "{:%Y-%m-%d}".format(datetime.now())

    # the transactions in the response are paginated, so make multiple calls while increasing the offset to
    # retrieve all transactions
    transactions = []
    total_transactions = 1
    first_response = None
    while len(transactions) < total_transactions:
        try:
            response = client.Transactions.get(
                access_token, start_date, end_date, offset=len(transactions)
            )
        except plaid.errors.PlaidError as e:
            logging.warning("Plaid error: %s", e.message)
            return
        transactions.extend(response["transactions"])
        if first_response is None:
            first_response = response
            total_transactions = response["total_transactions"]
        if args.debug:
            pretty_print_response(response)

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
            posting = data.Posting(
                account["name"], Amount(-amount, currency), None, None, None, None
            )
            ref = data.new_metadata("foo", 0)
            entry = data.Transaction(
                ref,
                date.fromisoformat(transaction["date"]),
                flags.FLAG_OKAY,
                transaction["name"],
                "",  # memo
                data.EMPTY_SET,
                data.EMPTY_SET,
                [posting],
            )
            ledger.append(entry)
        ledger.reverse()  # API returns transactions in reverse chronological order
        # print entries to stdout
        print("; = {}, {} =".format(account["name"], currency))
        print("; {} transactions\n".format(len(ledger)))
        # look for duplicates
        ledger_with_dupes = find_duplicate_entries(ledger)
        # print the entries
        for entry in ledger_with_dupes:
            out = printer.format_entry(entry)
            if DUPLICATE_META in entry.meta:
                out = textwrap.indent(out, "; ")
            print(out)
        # find and print the balance directive
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
                entry = data.Balance(
                    meta,
                    date.today(),
                    account["name"],
                    Amount(bal, currency),
                    None,
                    None,
                )
                out = printer.format_entry(entry)
                print(out)

    logging.info("Done %s", name)
    print()


def fetch_balance(name, item, access_token):
    try:
        response = client.Accounts.get(access_token)
    except plaid.errors.PlaidError as e:
        logging.warning("Plaid error: %s", e.message)
        return
    if args.debug:
        pretty_print_response(response)

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
        assert account_def["currency"] == account_res["balances"]["iso_currency_code"]
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
        entry = data.Balance(
            meta,
            date.today(),
            account_def["name"],
            Amount(bal, account_def["currency"]),
            None,
            None,
        )
        out = printer.format_entry(entry)
        print("; = {}, {} =".format(account_def["name"], account_def["currency"]))
        print(out)
    logging.info("Done %s", name)
    print()


def check_that_op_is_present():
    """1Password CLI: https://support.1password.com/command-line/"""
    # check that op is installed, this will throw if not
    subprocess.run(
        ["op", "--version"],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def fetch_creds_from_op(item):
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


def find_duplicate_entries(new_entries):
    """Flag potentially duplicate entries.
    Args:
      new_entries: A list of lists of imported entries, one for each
        importer.
    Returns:
      A list of modified new entries (like new_entries), potentially with
        modified metadata to indicate those which are duplicated.
    """
    entries_with_dupes = []

    # Find similar entries against the existing ledger only.
    duplicate_pairs = similar.find_similar_entries(new_entries, existing_entries)

    # Add a metadata marker to the extracted entries for duplicates.
    duplicate_set = set(id(entry) for entry, _ in duplicate_pairs)
    for entry in new_entries:
        if id(entry) in duplicate_set:
            marked_meta = entry.meta.copy()
            marked_meta[DUPLICATE_META] = True
            entry = entry._replace(meta=marked_meta)
        entries_with_dupes.append(entry)

    return entries_with_dupes


def pretty_print_response(response):
    print(json.dumps(response, indent=2, sort_keys=True), file=sys.stderr)


def print_error(*args, **kwargs):
    print(file=sys.stderr, *args, **kwargs)


if __name__ == "__main__":
    run()
