import datetime
from decimal import Decimal
from typing import Optional, TypedDict, List

from beancount.core.data import (
    Directive,
    Posting,
    Amount,
)


class AmountJSON(TypedDict):
    number: Optional[Decimal]
    currency: str


class PostingJSON(TypedDict):
    account: str
    units: AmountJSON


class DirectiveJSON(TypedDict):
    date: datetime.date
    filename: str
    lineno: int
    payee: str
    narration: str
    postings: List[PostingJSON]


def _amount_to_json(amt: Amount) -> AmountJSON:
    return {
        "number": amt.number,
        "currency": amt.currency,
    }


def _posting_to_json(posting: Posting) -> PostingJSON:
    return {
        "account": posting.account,
        "units": _amount_to_json(posting.units),
    }


def txn_to_json(entry: Directive) -> DirectiveJSON:
    return {
        "date": entry.date,
        "filename": entry.meta["filename"],
        "lineno": entry.meta["lineno"],
        "payee": entry.payee,
        "narration": entry.narration,
        "postings": [_posting_to_json(p) for p in entry.postings],
    }
