"""modui: what an app asks the person, in the shape of the app SDK's `modui`.

A review is a set of facts the person reads before answering. A fact says what
it is - words, a sum, something compared character by character, raw bytes, a
note, a warning - and each model decides how that kind looks. The extapp driver
maps an app's request onto these calls, and core's own flows can make the same
calls.

A refusal raises `ActionCancelled`. A request the screens cannot draw raises
`ValueError`: more extras than the menu has room for, more than one `data` field
in one list of facts, or a summary with neither amount nor fee.
"""

from typing import TYPE_CHECKING

import trezormodui
from trezor import TR
from trezormodui import (
    ADDRESS,
    AMOUNT,
    CONFIRM,
    DANGER,
    DATA,
    DETAILS,
    NOTE,
    STRONG,
    TEXT,
    WARNING,
)

from . import pages

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Sequence

    from .pages import Field


def text(label: str, value: str) -> "Field":
    """Words or a number, shown as written."""
    return (TEXT, label, value)


def amount(label: str, value: str, ticker: str) -> "Field":
    """A sum as the person should read it, and the ticker of what it counts."""
    return (AMOUNT, label, f"{value} {ticker}")


def address(label: str, value: str) -> "Field":
    """Something compared character by character: grouped and fixed-width."""
    return (ADDRESS, label, value)


def data(label: str, value: bytes) -> "Field":
    """Raw bytes of any length, shown as hex and paged."""
    return (DATA, label, value)


def data_source(
    label: str, total: int, read: "Callable[[int, int], Awaitable[bytes]]"
) -> "Field":
    """Raw bytes read while the person pages: `read(offset, length)` returns
    them, in order, from the start, each range once."""
    return (DATA, label, pages.Source(total, read))


def note(text: str) -> "Field":
    """A sentence with no label: a question or an explanation."""
    return (NOTE, None, text)


def warning(text: str) -> "Field":
    """A sentence to weigh before confirming, drawn as a caution row."""
    return (WARNING, None, text)


class Extra:
    """Facts the person can open from a review's menu, under a label of their
    own. An extra with no facts is not offered."""

    def __init__(self, label: str, fields: "Sequence[Field]") -> None:
        self.label = label
        self.fields = fields


class Review:
    """A review waiting for its answer; see `review`."""

    def __init__(self, step: str, title: str, fields: "Sequence[Field]") -> None:
        self.step = step
        self.title = title
        self.fields = fields
        self._extras: "Sequence[Extra]" = ()

    def extras(self, extras: "Sequence[Extra]") -> "Review":
        """Facts the person can open from the menu and come back from.

        Each offered extra takes one entry of the menu, the way out one, and
        "Show all" of `details` one: a review offers up to five, `details`
        four, and `confirm_danger` none.
        """
        self._extras = extras
        return self

    async def confirm(self) -> None:
        """A tap, with the menu for the extras and the way out."""
        await self._answer(CONFIRM)

    async def confirm_strong(self) -> None:
        """A strong yes before signing or acting: a deliberate confirmation,
        drawn as a hold where the model has one."""
        await self._answer(STRONG)

    async def confirm_danger(self) -> None:
        """Going on is risky: refusing is the default, going on a detour."""
        await self._answer(DANGER)

    async def details(self) -> bool:
        """The short version, with "Show all" in the menu. `True` when the
        person picked it, `False` when they confirmed without the details."""
        return await self._answer(DETAILS)

    def _answer(self, answer: int) -> "Awaitable[bool]":
        return pages.review(self.step, self.title, self.fields, self._extras, answer)


def review(step: str, title: str, fields: "Sequence[Field]") -> Review:
    """Facts for the person to read, then answer. `step` names the screen's
    ButtonRequest."""
    return Review(step, title, fields)


class Summary:
    """A transfer's summary; see `summary`."""

    def __init__(self, step: str, title: str) -> None:
        self.step = step
        self.title = title
        self._amount: "Field | None" = None
        self._fee: "Field | None" = None
        self._account: Extra | None = None
        self._fee_info: Extra | None = None

    def amount(self, label: str, value: str, ticker: str) -> "Summary":
        """The amount that leaves."""
        self._amount = amount(label, value, ticker)
        return self

    def fee(self, label: str, value: str, ticker: str) -> "Summary":
        """The fee."""
        self._fee = amount(label, value, ticker)
        return self

    def account(self, title: str, fields: "Sequence[Field]") -> "Summary":
        """The account the transfer is signed from, offered in the menu."""
        self._account = Extra(title, fields)
        return self

    def fee_info(self, title: str, fields: "Sequence[Field]") -> "Summary":
        """The fee's details, offered in the menu."""
        self._fee_info = Extra(title, fields)
        return self

    async def confirm_strong(self) -> None:
        """The last yes before the transfer is signed: a strong review of the
        amount and the fee, with the account and the fee's details as its
        extras."""
        facts = [fact for fact in (self._amount, self._fee) if fact is not None]
        if not facts:
            raise ValueError("a summary needs an amount or a fee")
        extras = [
            extra for extra in (self._account, self._fee_info) if extra is not None
        ]
        await review(self.step, self.title, facts).extras(extras).confirm_strong()


def summary(step: str, title: str) -> Summary:
    """The last yes before signing a transfer, with the values of core's own
    summary screen."""
    return Summary(step, title)


async def verify_address(
    step: str, address: str, account: str | None = None, path: str | None = None
) -> None:
    """One of the person's own addresses, to check against the host's."""
    await pages.verify(
        trezormodui.verify_address,
        step,
        TR.address__confirmed,
        address=address,
        account=account,
        path=path,
    )


async def verify_pubkey(
    step: str, pubkey: str, account: str | None = None, path: str | None = None
) -> None:
    """One of the person's own public keys, to check against the host's."""
    await pages.verify(
        trezormodui.verify_pubkey,
        step,
        TR.address__public_key_confirmed,
        pubkey=pubkey,
        account=account,
        path=path,
    )


async def done(step: str, text: str) -> None:
    """The end of the flow, such as "Transaction signed"."""
    await pages.done(step, text)
