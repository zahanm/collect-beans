import argparse
import csv
from io import StringIO
import subprocess
from tempfile import NamedTemporaryFile

import matplotlib.pyplot as plt
import numpy as np

OUT_FILE = "out.png"
QUERY = """
select
    date,
    root(account, 2) as category,
    position
where account ~ 'Expenses:'
    and not account ~ 'Expenses:Taxes:'
    and date > #"Mar 1 2020"
limit 10;
"""

args = None


def run():
    parser = argparse.ArgumentParser(description="Analyse spending")
    parser.add_argument("journal", help="Journal file with beancount transations")
    global args
    args = parser.parse_args()
    with NamedTemporaryFile(mode="w+") as outfile:
        bean_query(outfile)
        parse(outfile)
    plot()


def bean_query(outfile):
    _ret = subprocess.run(
        [
            "bean-query",
            args.journal,
            QUERY,
            "--format",
            "csv",
            "--output",
            outfile.name,
        ],
        check=True,
        text=True,
    )


def parse(outfile):
    reader = csv.DictReader(outfile)
    for row in reader:
        print(row["date"])


def plot():
    _fig, ax = plt.subplots()
    ax.plot([1, 2, 3, 4], [1, 4, 2, 3])
    plt.savefig(OUT_FILE)
    subprocess.run(["open", OUT_FILE])


if __name__ == "__main__":
    run()
