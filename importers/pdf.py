"""Attempt at an importer for PDF statements.
For pay statements, mostly.
"""

import datetime
from os import path
import re
from subprocess import run, DEVNULL
from tempfile import NamedTemporaryFile

from dateutil.parser import parse as parse_datetime

from beancount.ingest import importer


def is_pdftotext_installed():
    """Return true if the external tool is installed."""
    run(["pdftotext", "--help"], check=True, stdout=DEVNULL, stderr=DEVNULL)
    return True


def pdf_to_text(filename):
    """Convert a PDF file to a text equivalent.

    Args:
      filename: A string path, the filename to convert.
    Returns:
      A string, the text contents of the filename.
    """
    assert is_pdftotext_installed(), "You need to install `poppler` for `pdftotext`"
    outfile = NamedTemporaryFile()
    done = run(["pdftotext", filename, outfile.name], capture_output=True, text=True)
    if done.returncode != 0 or done.stderr:
        raise ValueError(done.stderr)
    return outfile.read().decode()


class Importer(importer.ImporterProtocol):
    """An importer for PDF pay statements."""

    def __init__(self, account, content_regexp=None, file_prefix=None):
        self.account = account
        self.content_regexp = content_regexp
        self.file_prefix = file_prefix

    def identify(self, file):
        if file.mimetype() != "application/pdf":
            return False

        # Look for words in the PDF file.
        # The filename they provide isn't useful.
        text = file.convert(pdf_to_text)
        if text and self.content_regexp:
            return re.search(self.content_regexp, text, flags=re.IGNORECASE) is not None

    def file_name(self, _):
        # Noramlize the name to something meaningful.
        return self.file_prefix

    def file_account(self, _):
        return self.account

    def file_date(self, file):
        # Get the actual statement's date from the contents of the file.
        text = file.convert(pdf_to_text)
        match = re.match(r"^(\d{2}/\d{2}/\d{4})$", text)
        if match:
            return parse_datetime(match.group(1)).date()
