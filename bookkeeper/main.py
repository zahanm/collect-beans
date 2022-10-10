import yaml

import sys


class Runner:
    """
    Interactive workflow to collect and categorise transations from Plaid for my Beancounting process.
    Collect = Gather transations from Plaid for the accounts defined in my ledger / config.
    Categorise = suggest an expense account for transactions from the ledger that are missing one.
    """

    def __init__(self, config: str):
        with open(config) as f:
            self.config = f.read()  # yaml.full_load(f)

    def run(self):
        print(sys.argv)
        print(self.config[:25])


if __name__ == "__main__":
    r = Runner(sys.argv[1])
    r.run()
