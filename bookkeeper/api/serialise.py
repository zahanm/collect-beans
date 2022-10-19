from typing import Any, Dict

from beancount.core.data import (
    Directive,
    Posting,
    Amount,
)


# class AmountJSON(TypedDict):
#     number: Optional[Decimal]
#     currency: str


# class PostingJSON(TypedDict):
#     account: str
#     units: AmountJSON
#     flag: Optional[str]
#     # cost
#     # price


# Matches the definition of beancount.core.data.Transaction
# class DirectiveJSON(TypedDict):
#     date: datetime.date
#     filename: str
#     lineno: int
#     payee: Optional[str]
#     narration: str
#     postings: List[PostingJSON]
#     flag: str
#     tags: Set[str]
#     links: Set[str]


class DirectiveWithID:
    id: int
    entry: Directive

    def __init__(self, id: int, entry: Directive) -> None:
        self.id = id
        self.entry = entry


def to_dict(item: Any) -> Dict:
    if isinstance(item, DirectiveWithID):
        return {
            "id": item.id,
            "entry": to_dict(item.entry),
        }
    elif isinstance(item, Directive):
        return {
            "date": item.date,
            "filename": item.meta["filename"],
            "lineno": item.meta["lineno"],
            "payee": item.payee,
            "narration": item.narration,
            "postings": [to_dict(p) for p in item.postings],
            "flag": item.flag,
            "tags": list(item.tags),  # set is not serialisable
            "links": list(item.links),
        }
    elif isinstance(item, Posting):
        return {
            "account": item.account,
            "units": to_dict(item.units),
            "flag": item.flag,
        }
    elif isinstance(item, Amount):
        return {
            "number": item.number,
            "currency": item.currency,
        }
    else:
        raise RuntimeError("Unexpected type passed to_dict(): {}".format(type(item)))
