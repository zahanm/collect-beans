"""Import configuration."""

# Insert our custom importers path here.
import sys
from os import path
sys.path.insert(0, path.join(path.dirname(__file__)))

from importers import firstpub, amex

from beancount.ingest import extract
from beancount.ingest.importers import csv
from beancount.ingest.scripts_utils import ingest
from ofxclient import Institution
from ofxhome import OFXHome
from os import path
import shutil
import sys
import yaml

# if this is the download flow
if len(sys.argv) > 1 and sys.argv[1] == 'download':
    # load accounts config
    fname = path.join(path.dirname(__file__), 'CONFIG.yaml')
    with open(fname) as f:
        CONFIG = yaml.load(f)
    # look up and download for each
    for name, importer in CONFIG.items():
        print('Importer:', name)
        bank = OFXHome.lookup(importer['OFX-ID'])
        print('Bank:', bank.name)
        client = Institution(bank.fid, bank.org, bank.url, importer['username'], importer['pw'])
        assert len(client.accounts()) == 1
        acc = client.accounts()[0]
        print('Fetching:', acc.long_description())
        statement = acc.download(days=5)
        fname = name + '_' + acc.number_masked()[-4:] + '.ofx'
        print('Writing:', fname)
        with open(fname, 'w') as f:
            shutil.copyfileobj(statement, f)
    # done
    exit(0)

# otherwise, go through the regular `bean-{identify,extract,file}` flow

# Setting this variable provides a list of importer instances.
importers = [
]

# Override the header on extracted text (if desired).
extract.HEADER = ';; -*- mode: org; mode: beancount; coding: utf-8; -*-\n'

ingest(importers)
