from beancount.ingest import importer


class Importer(importer.ImporterProtocol):
    """An importer that does nothing."""

    def __init__(self, account):
        self.account = account

    def identify(self, file):
        return False

    def file_account(self, _):
        return self.account
