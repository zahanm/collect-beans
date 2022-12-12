from dataclasses import dataclass
from typing import Any, Dict, Optional, Set

from beancount.core.data import (
    Directive,
    Posting,
    Amount,
)
from beancount.core.number import D


class DirectiveForSort:
    id: str
    entry: Directive
    auto_category: Optional[str]

    def __init__(
        self, id: str, entry: Directive, autocat: Optional[str] = None
    ) -> None:
        self.id = id
        self.entry = entry
        self.auto_category = autocat


def to_dict(item: Any) -> Dict:
    if isinstance(item, DirectiveForSort):
        return {
            "id": item.id,
            "auto_category": item.auto_category,
            "entry": to_dict(item.entry),
        }
    elif isinstance(item, Directive):
        return {
            "date": item.date.isoformat(),
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
    elif isinstance(item, DirectiveMod):
        return {
            "id": item.id,
            "type": item.type,
            "postings": [to_dict(p) for p in item.postings] if item.postings else None,
            "payee": item.payee,
            "narration": item.narration,
        }
    else:
        raise RuntimeError("Unexpected type passed to_dict(): {}".format(type(item)))


@dataclass
class DirectiveMod:
    id: str
    type: str
    postings: Optional[Set[Posting]]
    payee: Optional[str]
    narration: Optional[str]
    # date: datetime.date
    # filename: str
    # lineno: int


def _posting_from_dict(item: Any) -> Posting:
    return Posting(
        account=item["account"],
        units=Amount(
            number=D(item["units"]["number"]),
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


def mod_from_dict(item: Any) -> DirectiveMod:
    mod = DirectiveMod(
        id=item["id"],
        type=item["type"],
        postings={_posting_from_dict(p) for p in item["postings"]}
        if "postings" in item
        else None,
        payee=item["payee"] if "payee" in item else None,
        narration=item["narration"] if "narration" in item else None,
    )
    return mod


@dataclass(frozen=True)
class Account:
    name: str
    plaid_id: str
    currency: str


@dataclass(frozen=True)
class Importer:
    name: str
    access_token: str
    institution_id: str
    accounts: Set[Account]


def importer_from_dict(item: Any) -> Importer:
    return Importer(
        name=item["name"],
        access_token=item["access_token"],
        institution_id=item["institution_id"],
        accounts={_account_from_dict(a) for a in item["accounts"]},
    )


def _account_from_dict(item: Any) -> Account:
    return Account(
        name=item["name"], plaid_id=item["plaid_id"], currency=item["currency"]
    )
