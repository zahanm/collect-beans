"""Import configuration."""

# Insert our custom importers path here.
import sys
from os import path
sys.path.insert(0, path.join(path.dirname(__file__)))

from importers import firstpub, amex
import collector

from beancount.ingest import extract
from beancount.ingest.importers import ofx
from beancount.ingest.scripts_utils import ingest
import yaml

# load accounts config
fname = path.join(path.dirname(__file__), 'CONFIG.yaml')
with open(fname) as f:
    CONFIG = yaml.load(f)

# if this is the download flow
if len(sys.argv) > 1 and sys.argv[1] == 'download':
    collector.run(CONFIG)
    exit(0)

# otherwise, go through the regular `bean-{identify,extract,file}` flow

def make_importer(account):
    return ofx.Importer(
        account['account-id'],
        account['name'],
        balance_type=ofx.BalanceType.LAST)

importers = map(make_importer, CONFIG.values())

# Override the header on extracted text (if desired).
extract.HEADER = ';; -*- mode: org; mode: beancount; coding: utf-8; -*-\n'

ingest(importers)
