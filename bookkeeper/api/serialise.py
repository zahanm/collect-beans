from decimal import Decimal
from typing import Any, Dict, Set, Type, TypeVar, TypedDict

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
    id: str
    entry: Directive

    def __init__(self, id: str, entry: Directive) -> None:
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
            # "flag": item.flag,
            # "filename": item.meta["filename"] if item.meta is not None else None,
            # "lineno": item.meta["lineno"] if item.meta is not None else None,
        }
    elif isinstance(item, Amount):
        return {
            "number": item.number,
            "currency": item.currency,
        }
    else:
        raise RuntimeError("Unexpected type passed to_dict(): {}".format(type(item)))


# T = TypeVar("T", DirectiveWithID, Directive, Posting, Amount)


# def from_dict(item: Any, cls: Type[T]) -> T:
#     if cls == DirectiveWithID:
#         return DirectiveWithID(id=item["id"], entry=from_dict(item["entry"], Directive))
#     elif cls == Directive:
#         return Amount(0, "USD")
#     elif cls == Posting:
#         return Amount(0, "USD")
#     elif cls == Amount:
#         return Amount(0, "USD")
#     else:
#         raise RuntimeError("Unexpected type passed to from_dict(): {}".format(cls))


# class AmountMod(TypedDict):
#     number: Decimal
#     currency: str


# class PostingMod(TypedDict):
#     account: str
#     units: AmountMod


class DirectiveMod(TypedDict):
    id: str
    postings: Set[Posting]
    # date: datetime.date
    # filename: str
    # lineno: int
    # payee: Optional[str]
    # narration: str


def _posting_from_dict(item: Any) -> Posting:
    return Posting(
        account=item["account"],
        units=Amount(
            number=item["units"]["number"],
            currency=item["units"]["currency"],
        ),
        # flag=item["flag"],
        flag=None,
        # meta={
        #     "filename": item["filename"],
        #     "lineno": item["lineno"],
        # },
        meta=None,
        cost=None,
        price=None,
    )


def from_dict(item: Any) -> DirectiveMod:
    pp = set()
    return DirectiveMod(
        id=item["id"],
        postings={_posting_from_dict(p) for p in item["postings"]},
    )
