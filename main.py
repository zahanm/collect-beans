"""Import configuration."""

from importers import ofx, csv
import collector

from beancount.ingest import extract
from beancount.ingest.scripts_utils import ingest

from os import path
import sys
import yaml

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

# if this is the download flow
if "collect" in sys.argv:
    collector.run(CONFIG)
    exit(0)

# otherwise, go through the regular `bean-{identify,extract,file}` flow


def make_importer(item):
    (name, account) = item
    if account["importer"] == "OFX":
        return ofx.Importer(account["name"], account["currency"], account["account-id"])
    elif account["importer"] == "CSV":
        return csv.Importer(
            account["column_map"],
            account["name"],
            account["currency"],
            content_regexp=account.get("content_regexp"),
            filename_regexp=account.get("filename_regexp"),
            file_prefix=name,
        )
    else:
        assert False, "Invalid importer: " + repr(account)


importers = map(make_importer, CONFIG.items())

ingest(importers)
