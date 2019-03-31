"""Import configuration."""

from itertools import chain
from os import path
import sys
import yaml

from beancount.ingest import extract
from beancount.ingest.scripts_utils import ingest

from importers import ofx, csv, pdf, dummy
import collector

# import argparse
# parser = argparse.ArgumentParser(description="Collecting beans")
# parser.add_argument('--collect-config', required=True, help='CONFIG.yaml file location')
# parser.add_argument('action', help='download, or the bean-* commands')
# (args, _) = parser.parse_known_args()
# print(args.collect_config)

# load accounts config
# FIXME: hard-coded for now, see beancount issue https://bitbucket.org/blais/beancount/issues/358/
fname = path.join(path.dirname(__file__), "../accounts/CONFIG.yaml")
with open(fname) as f:
    CONFIG = yaml.load(f)

# go through the regular `bean-{identify,extract,file}` flow


def make_importers(item):
    (credentials_name, institution) = item

    def importer(account):
        if institution["importer"] == "OFX":
            return ofx.Importer(account["name"], institution["currency"], account["id"])
        elif institution["importer"] == "CSV":
            return csv.Importer(
                institution["column_map"],
                account["name"],
                institution["currency"],
                content_regexp=account.get("content_regexp"),
                filename_regexp=account.get("filename_regexp"),
                file_prefix=credentials_name + account["id"],
            )
        elif institution["importer"] == "PDF":
            return pdf.Importer(
                account["name"],
                content_regexp=account.get("content_regexp"),
                filing_name=account.get("filing_name"),
            )
        elif institution["importer"] == "custom":
            return dummy.Importer(account["name"])
        else:
            assert False, "Invalid importer: " + repr(institution) + " " + repr(account)

    return map(importer, institution["accounts"])


# the list(..) turns this from an iterable to a materialized list
importers = list(
    # aka, flatten(..)
    chain.from_iterable(map(make_importers, CONFIG["importers"].items()))
)
ingest(importers)
