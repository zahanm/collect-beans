import argparse
import csv
from datetime import date, timedelta
from io import StringIO
import subprocess
from tempfile import NamedTemporaryFile

from beancount.core.amount import Amount
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

OUT_FILE = "out.png"
QUERY = """
select
    date,
    root(account, 2) as category,
    convert(position, 'USD') as spend
where account ~ '^Expenses:'
    and not account ~ '^Expenses:Taxes:'
    and date > #"{start}";
"""

args = None


def run():
    parser = argparse.ArgumentParser(description="Analyse spending")
    parser.add_argument("journal", help="Journal file with beancount transations")
    global args
    args = parser.parse_args()
    with NamedTemporaryFile(mode="w+") as outfile:
        bean_query(outfile)
        data = parse(outfile)
    plot(data)


def bean_query(outfile):
    _ret = subprocess.run(
        [
            "bean-query",
            args.journal,
            QUERY.format(start=get_start().isoformat()),
            "--format",
            "csv",
            "--output",
            outfile.name,
        ],
        check=True,
        text=True,
    )


def parse(outfile):
    data = pd.read_csv(
        outfile,
        parse_dates=[0],
        converters={
            "category": lambda x: x.split(":")[1].strip(),
            "spend": lambda x: pd.to_numeric(Amount.from_string(x).number),
        },
    )
    start = get_start()
    end = date.today()
    bins = pd.date_range(
        start=start, end=end, freq=pd.offsets.Week(weekday=end.weekday())
    )
    data["bin"] = pd.cut(data["date"], bins)
    print(data)
    return data


def plot(data):
    daily_spend = data.groupby(["bin", "category"])
    _categories = np.unique(data["category"])
    table = daily_spend.sum()["spend"].unstack()
    fig, ax = plt.subplots()
    table.plot.bar(ax=ax)
    datelabels = [interval.left.strftime("%d %b") for interval in table.index]
    ax.set_xlabel(None)
    ax.set_xticklabels(datelabels)
    fig.autofmt_xdate()
    plt.savefig(OUT_FILE)
    subprocess.run(["open", OUT_FILE])


def get_start():
    return date.today() - timedelta(weeks=12)


if __name__ == "__main__":
    run()
