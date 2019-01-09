"""Import configuration."""

# Insert our custom importers path here.
import sys
from os import path
sys.path.insert(0, path.join(path.dirname(__file__)))

from importers import ofx, csv
import collector

from beancount.ingest import extract
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
    if account['importer'] == 'OFX':
        return ofx.Importer(
            account['account-id'],
            account['name'],
            account['currency'])
    elif account['importer'] == 'CSV':
        return csv.Importer(
            account['column_map'],
            account['name'],
            account['currency'],
            content_regexp=account.get('content_regexp'),
            filename_regexp=account.get('filename_regexp'))
    else:
        assert False, 'Invalid importer: ' + repr(account)

importers = map(make_importer, CONFIG.values())

ingest(importers)
