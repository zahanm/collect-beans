#!/usr/bin/env python3
"""Import configuration."""

from itertools import chain
from os import path
import yaml

from importers import ofx, csv, pdf, dummy

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
    CONFIGyaml = yaml.full_load(f)

# go through the regular `bean-{identify,extract,file}` flow


def make_importers(item):
    (credentials_name, institution) = item

    def importer(account):
        importer = institution.get("importer")
        if importer == "OFX":
            account_id = account["number"] if "number" in account else account["id"]
            return ofx.Importer(account["name"], account["currency"], account_id)
        elif importer == "CSV":
            return csv.Importer(credentials_name, institution, account)
        elif importer == "PDF":
            return pdf.Importer(
                account["name"],
                content_regexp=account.get("content_regexp"),
                filing_name=account.get("filing_name"),
            )
        elif importer == "custom":
            return dummy.Importer(account["name"])
        else:
            return None

    return [ii for ii in map(importer, institution["accounts"]) if ii is not None]


# the list(..) turns this from an iterable to a materialized list
CONFIG = list(
    # aka, flatten(..)
    chain.from_iterable(map(make_importers, CONFIGyaml["importers"].items()))
)
