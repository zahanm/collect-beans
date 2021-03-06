import argparse
import csv
from datetime import date, timedelta
import logging
import subprocess
import sys
from tempfile import NamedTemporaryFile

from beancount.core.amount import Amount
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

OUT_FILE = "out.png"
QUERY = """
select
    date,
    root(account, 2) as category,
    account,
    convert(position, 'USD') as spend
where account ~ '^Expenses:'
    {exclusions}
    {inclusions}
    and date > #"{start}";
"""
EXCLUSION = """
and not account ~ '^{account}'
"""
INCLUSION = """
and account ~ '^{account}'
"""

args = None
logger = None


def run():
    parser = argparse.ArgumentParser(description="Analyse spending")
    parser.add_argument("journal", help="Journal file with beancount transations")
    parser.add_argument(
        "--monthly",
        action="store_true",
        help="Look at spend per month for half a year",
    )
    parser.add_argument(
        "--debug", action="store_true", help="Output debug logs to stderr",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        help="Exclude this account/prefix from the analysis (can specify multiple). f.e. Expenses:Home:",
        default=[],
    )
    parser.add_argument(
        "--only",
        action="append",
        help="Include only this account/prefix from the analysis (can specify multiple). f.e. Expenses:Home:Utilities",
        default=[],
    )
    parser.add_argument(
        "--full-account",
        action="store_true",
        help="Use the full account name as group-by",
    )
    global args, logger
    args = parser.parse_args()
    logger = logging.getLogger(__name__)
    logger.addHandler(logging.StreamHandler())
    logger.setLevel(logging.DEBUG if args.debug else logging.WARNING)
    with NamedTemporaryFile(mode="w+") as outfile:
        bean_query(outfile)
        data = parse(outfile)
    plot(data)


def bean_query(outfile):
    exclusions = [EXCLUSION.strip().format(account=ex) for ex in args.exclude]
    inclusions = [INCLUSION.strip().format(account=inc) for inc in args.only]
    query = QUERY.format(
        start=get_start().isoformat(),
        exclusions="\n".join(exclusions),
        inclusions="\n".join(inclusions),
    ).strip()
    logger.debug(query)
    _ret = subprocess.run(
        [
            "bean-query",
            args.journal,
            query,
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
            "account": lambda x: ":".join(x.split(":")[1:]).strip(),
            "spend": lambda x: pd.to_numeric(Amount.from_string(x).number),
        },
    )
    start = get_start()
    end = get_end()
    freq = (
        pd.offsets.MonthBegin()
        if args.monthly
        else pd.offsets.Week(weekday=end.weekday())
    )
    bins = pd.date_range(start=start, end=end, freq=freq)
    data["bin"] = pd.cut(data["date"], bins)
    return data


def plot(data):
    if args.full_account:
        group_by = "account"
    else:
        group_by = "category"
    daily_spend = data.groupby(["bin", group_by])
    table = daily_spend.sum()["spend"].unstack()
    sns.set()
    fig, ax = plt.subplots()
    fig.set_size_inches(12.8, 8.8)
    table.plot.bar(ax=ax, stacked=True)
    datelabels = [interval.left.strftime("%d %b") for interval in table.index]
    ax.set_xlabel(None)
    ax.set_xticklabels(datelabels)
    fig.autofmt_xdate()
    plt.savefig(OUT_FILE)
    subprocess.run(["open", OUT_FILE])


def get_start():
    if args.monthly:
        old = date.today() - timedelta(days=6 * 30)
        return old.replace(day=1)  # start from first of month
    else:
        return date.today() - timedelta(weeks=12)


def get_end():
    if args.monthly:
        new = date.today() + timedelta(days=30)
        return new.replace(day=1)  # end on first day of next month
    else:
        return date.today()


if __name__ == "__main__":
    run()
