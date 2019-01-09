"""Import configuration."""

# Insert our custom importers path here.
import sys
from os import path
sys.path.insert(0, path.join(path.dirname(__file__)))

from importers import firstpub, amex
import collector

from beancount.ingest import extract
from beancount.ingest.importers import csv
from beancount.ingest.scripts_utils import ingest


# if this is the download flow
if len(sys.argv) > 1 and sys.argv[1] == 'download':
    collector.run()
    exit(0)

# otherwise, go through the regular `bean-{identify,extract,file}` flow

# Setting this variable provides a list of importer instances.
importers = [
]

# Override the header on extracted text (if desired).
extract.HEADER = ';; -*- mode: org; mode: beancount; coding: utf-8; -*-\n'

ingest(importers)
