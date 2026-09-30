from typing import *
from buffer_types import *
WardError: type[Exception]


# rust/src/ward/micropython.rs
def get(wallet_id: AnyBytes, app: AnyBytes, key: AnyBytes) -> bytes | None:
    """
    Return the value stored under `key` for the given wallet and app,
    or None if there is no such record.
    """


# rust/src/ward/micropython.rs
def next_entry(wallet_id: AnyBytes, app: AnyBytes, cursor: int) -> tuple[int, bytes, bytes] | None:
    """
    Return `(next_cursor, key, value)` of the next record of the given
    wallet and app from `cursor` on, or None if there is none left.
    The cursor is opaque: iteration starts with 0 and continues with
    `next_cursor`. The order of the records is unspecified, and so are
    the results if any store is modified in between.
    """


# rust/src/ward/micropython.rs
def set(wallet_id: AnyBytes, app: AnyBytes, key: AnyBytes, value: AnyBytes) -> None:
    """
    Store `value` under `key` for the given wallet and app, replacing an
    existing value in place. Raise WardError if the record does not fit.
    """


# rust/src/ward/micropython.rs
def delete(wallet_id: AnyBytes, app: AnyBytes, key: AnyBytes) -> bool:
    """
    Delete the record stored under `key` for the given wallet and app.
    Return whether a record was deleted.
    """
