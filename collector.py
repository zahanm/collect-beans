import argparse
import json
import logging
from ofxclient import Institution
from ofxhome import OFXHome
from os import path
import shutil
import subprocess
import sys
import yaml
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
    if any(acc["downloader"] == "OFX" for acc in importers.values()):
        session = sign_in_to_op()

    # look up and download for each
    for name, account in importers.items():
        if account["downloader"] == "OFX":
            ofx(args, session, name, account)
        elif account["downloader"] == "custom":
            manual(args, name, account)
        else:
            assert False, "Invalid downloader: " + repr(account)
        print()


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


def manual(args, name, account):
    print("Account:", name)
    print("You need to download this", account["importer"], "by hand")
    print("Instructions:", account["instructions"])
    print("And put it in", args.out)


if __name__ == "__main__":
    run()
