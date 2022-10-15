import yaml

import argparse


class Runner:
    """
    Interactive workflow to collect and categorise transations from Plaid for my Beancounting process.
    Collect = Gather transations from Plaid for the accounts defined in my ledger / config.
    Categorise = suggest an expense account for transactions from the ledger that are missing one.
    """

    def __init__(self):
        args = self._extract_args()
        print(args)
        with open(args.config) as f:
            self.config = yaml.full_load(f)
        self.run = args.func

    def collect_and_sort(self):
        print("collect and sort")
        print(list(self.config["categories"].keys())[0])

    def sort_only(self):
        print("sort only")

    def collect_only(self):
        print("collect only")

    def _extract_args(self):
        parser = argparse.ArgumentParser(
            description="Collect and categorise transations. Takes them from $source, categorises them, and writes them to $destination."
        )
        parser.add_argument("--debug", action="store_true", help="Debug the steps")
        subp = parser.add_subparsers(help="Top level")
        everything = subp.add_parser("collect-and-sort", help="Does everything")
        everything.set_defaults(func=self.collect_and_sort)
        sort = subp.add_parser("sort-only", help="Only does categorisation step")
        sort.set_defaults(func=self.sort_only)
        collect = subp.add_parser("collect-only", help="Only does collection step")
        collect.set_defaults(func=self.collect_only)
        parser.add_argument(
            "config", help="YAML file with configuration for this collector"
        )
        return parser.parse_args()


if __name__ == "__main__":
    r = Runner()
    r.run()
