from ofxclient import Institution
from ofxhome import OFXHome
import plaid
import yaml

import argparse
from datetime import datetime, timedelta
import json
import logging
from os import getenv, path
import shutil
import subprocess
import sys
from typing import Any, Dict


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
        "--out", "-o", required=True, help="Which folder to store the .ofx files in."
    )
    parser.add_argument(
        "--debug", action="store_true", help="Debug the request and responses"
    )
    args = parser.parse_args()

    with open(args.config) as f:
        CONFIG = yaml.full_load(f)
    importers = CONFIG["importers"]

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    session = None
    if any(
        acc["downloader"] == "OFX" or acc["downloader"] == "plaid"
        for acc in importers.values()
    ):
        session = sign_in_to_op()

    # look up and download for each
    for name, account in importers.items():
        if account["downloader"] == "OFX":
            ofx(args, session, name, account)
        elif account["downloader"] == "custom":
            # manual(args, name, account)
            pass
        elif account["downloader"] == "plaid":
            plaid_fetch(args, session, name, account)
            print()
        else:
            assert False, "Invalid downloader: " + repr(account)


def ofx(args, session, name, account):
    print("Account:", name)
    bank = OFXHome.lookup(account["OFX-id"])
    print("Bank:", bank.name)
    proceed = input("Should I download on this run? (y/n): ")
    if proceed[:1] != "y":
        return
    (username, pw) = fetch_creds_from_op(session, account)
    print("Got credentials, now talking to bank.")
    client = Institution(bank.fid, bank.org, bank.url, username, pw)
    assert len(client.accounts()) > 0, "No accounts"
    for acc in client.accounts():
        print("Fetching:", acc.long_description())
        statement = acc.download(days=args.days)
        fname = path.join(args.out, name + "_" + acc.number_masked()[-4:] + ".ofx")
        print("Writing:", fname)
        with open(fname, "w") as f:
            shutil.copyfileobj(statement, f)


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

client = plaid.Client(
    client_id=PLAID_CLIENT_ID,
    secret=PLAID_SECRET,
    public_key=PLAID_PUBLIC_KEY,
    environment=PLAID_ENV,
    api_version="2019-05-29",
)


def plaid_fetch(args, session, name, account):
    print("Account:", name)
    proceed = input("Should I download on this run? (y/n): ")
    if proceed[:1] != "y":
        return
    (_, access_token) = fetch_plaid_creds_from_op(session, account)
    print("Got credentials, now talking to bank.")
    # Pull transactions for the last 30 days
    start_date = "{:%Y-%m-%d}".format(datetime.now() + timedelta(days=-2))
    end_date = "{:%Y-%m-%d}".format(datetime.now())
    try:
        transactions_response = client.Transactions.get(
            access_token, start_date, end_date
        )
    except plaid.errors.PlaidError as e:
        print("Plaid error:", e.code, e.type, e.display_message, file=sys.stderr)
        return
    pretty_print_response(transactions_response)


def pretty_print_response(response):
    print(json.dumps(response, indent=2, sort_keys=True))


def sign_in_to_op():
    """1Password CLI: https://support.1password.com/command-line/"""
    # check that op is installed, this will throw if not
    subprocess.run(
        ["op", "--version"],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    # sign in
    ret = subprocess.run(
        ["op", "signin", "--output=raw"],
        check=True,
        stderr=sys.stderr,
        stdin=sys.stdin,
        stdout=subprocess.PIPE,
        text=True,
    )
    session = ret.stdout
    return session


def fetch_creds_from_op(session, account):
    """fetch credentials from 1Password"""
    print("op get item", account["op-id"])
    # fetch the item
    ret = subprocess.run(
        ["op", "get", "item", account["op-id"]],
        check=True,
        text=True,
        input=session,
        stdout=subprocess.PIPE,
    )
    item = json.loads(ret.stdout)
    # parse out the username and password
    fields = item["details"]["fields"]
    assert any(f["designation"] == "username" for f in fields)
    assert any(f["designation"] == "password" for f in fields)
    for f in fields:
        if f["designation"] == "username":
            username = f["value"]
    for f in fields:
        if f["designation"] == "password":
            pw = f["value"]
    return (username, pw)


def fetch_plaid_creds_from_op(session, account):
    """fetch credentials from 1Password"""
    print("op get item", account["op-id"])
    # fetch the item
    ret = subprocess.run(
        ["op", "get", "item", account["op-id"]],
        check=True,
        text=True,
        input=session,
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


def manual(args, name, account):
    print("Account:", name)
    print("You need to download this", account["importer"], "by hand")
    print("Instructions:", account["instructions"])
    print("And put it in", args.out)


if __name__ == "__main__":
    run()
