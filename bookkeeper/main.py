import yaml

import argparse
import readline  # needed for input() to offer better support


class Runner:
    """
    Interactive workflow to collect and categorise transations from Plaid for my Beancounting process.
    Collect = Gather transations from Plaid for the accounts defined in my ledger / config.
    Categorise = suggest an expense account for transactions from the ledger that are missing one.
    """

    def __init__(self):
        args = self._extract_args()
        with open(args.config) as f:
            self.config = yaml.full_load(f)

    def run(self):
        op = self._get_op()
        if op == "2":
            self.sort()
        elif op == "3":
            self.collect()
        elif op == "1":
            self.collect()
            self.sort()
        print(list(self.config["categories"].keys())[0])

    def _get_op(self) -> str:
        print(
            """Which operations should we run?
1. collect-and-sort
2. sort-only
3. collect-only"""
        )
        op = input("Pick a choice? [1]: ").strip() or "1"
        if op not in [str(x) for x in range(1, 4)]:
            raise RuntimeError("Invalid choice")
        return op

    def sort(self):
        print("sort")

    def collect(self):
        print("collect")

    def _extract_args(self):
        parser = argparse.ArgumentParser(
            description="Collect and categorise transations. Takes them from $source, categorises them, and writes them to $destination."
        )
        parser.add_argument("--debug", action="store_true", help="Debug the script")
        parser.add_argument(
            "config", help="YAML file with configuration for this collector"
        )
        return parser.parse_args()


if __name__ == "__main__":
    r = Runner()
    r.run()
