"""Import configuration."""

# Insert our custom importers path here.
import sys
from os import path
sys.path.insert(0, path.join(path.dirname(__file__)))

from importers import firstpub, amex

from beancount.ingest import extract
from beancount.ingest.importers import csv
from beancount.ingest.scripts_utils import ingest
from os import path
import yaml

fname = path.join(path.dirname(__file__), 'CONFIG.yaml')
with open(fname) as f:
    CONFIG = yaml.load(f)

# Setting this variable provides a list of importer instances.
importers = [
]

# Override the header on extracted text (if desired).
extract.HEADER = ';; -*- mode: org; mode: beancount; coding: utf-8; -*-\n'

ingest(importers)
