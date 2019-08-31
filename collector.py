from beancount.core import flags
from beancount.core.number import D
from beancount.core.amount import Amount
from beancount.core import data
from beancount.parser import printer
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

client = None


def run():
    parser = argparse.ArgumentParser(description="Download statements from banks")
    parser.add_argument("config", help="YAML file with accounts configured")
    parser.add_argument(
        "--days",
        type=int,
        default=10,
        help="How many days back should the statement go?",
    )
    parser.add_argument(
        "--debug", action="store_true", help="Debug the request and responses"
    )
    args = parser.parse_args()

    with open(args.config) as f:
        CONFIG = yaml.full_load(f)
    importers = CONFIG["importers"]

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

    # look up and download for each
    for name, item in importers.items():
        if item["downloader"] != "plaid":
            continue
        fetch(args, name, item)


def fetch(args, name, item):
    logging.info("Item: %s", name)
    (_, access_token) = fetch_creds_from_op(item)
    logging.info("Got credentials, now talking to bank.")
    # Pull transactions for the last 30 days
    start_date = "{:%Y-%m-%d}".format(datetime.now() + timedelta(days=-args.days))
    end_date = "{:%Y-%m-%d}".format(datetime.now())
    try:
        transactions_response = client.Transactions.get(
            access_token, start_date, end_date
        )
    except plaid.errors.PlaidError as e:
        logging.warning("Plaid error: %s", e.message)
        return

    if args.debug:
        pretty_print_response(transactions_response)

    if "accounts" not in transactions_response:
        logging.warning("No accounts, aborting")
        return
    assert "accounts" in item
    currency = item["currency"]
    for account in item["accounts"]:
        # checking for every configured account in the response
        t_accounts = list(
            filter(
                lambda tacc: account["id"] == tacc["account_id"],
                transactions_response["accounts"],
            )
        )
        if len(t_accounts) == 0:
            logging.warning("Not present in response: %s", account["name"])
            continue
        assert len(t_accounts) == 1
        t_account = t_accounts[0]
        ledger = []
        # TODO handle pagination https://github.com/plaid/plaid-python#retrieve-transactions
        # transactions_response["total_transactions"]
        for transaction in transactions_response["transactions"]:
            if account["id"] != transaction["account_id"]:
                continue
            # assert currency == transaction["iso_currency_code"] skipping for now in sandbox
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
                transaction["name"],  # TODO titlecase First Republic at least
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
        for entry in ledger:
            out = printer.format_entry(entry)
            print(out)
        # find and print the balance directive
        if "current" in t_account["balances"]:
            bal = D(t_account["balances"]["current"])
            # sadly, plaid-python parses as `float` https://github.com/plaid/plaid-python/issues/136
            bal = round(bal, 2)
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


def pretty_print_response(response):
    print(json.dumps(response, indent=2, sort_keys=True), file=sys.stderr)


def print_error(*args, **kwargs):
    print(file=sys.stderr, *args, **kwargs)


if __name__ == "__main__":
    run()
