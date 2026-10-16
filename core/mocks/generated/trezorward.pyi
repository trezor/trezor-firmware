from typing import *
from buffer_types import *
WardError: type[Exception]


# rust/src/ward/micropython.rs
def get(wallet_id: AnyBytes, app: int, key: AnyBytes) -> bytes | None:
    """
    Return the value stored under `key` for the given wallet and app,
    or None if there is no such record.
    """


# rust/src/ward/micropython.rs
def next_entry(wallet_id: AnyBytes, app: int, cursor: int) -> tuple[int, bytes, bytes] | None:
    """
    Return `(next_cursor, key, value)` of the first record of the given
    wallet and app at or after `cursor`, or None if there is none left.
    Iteration starts with cursor 0 and continues with `next_cursor`.
    """


# rust/src/ward/micropython.rs
def set(wallet_id: AnyBytes, app: int, key: AnyBytes, value: AnyBytes) -> None:
    """
    Store `value` under `key` for the given wallet and app, replacing an
    existing value in place. Raise WardError if the record does not fit.
    """


# rust/src/ward/micropython.rs
def delete(wallet_id: AnyBytes, app: int, key: AnyBytes) -> bool:
    """
    Delete the record stored under `key` for the given wallet and app.
    Return whether a record was deleted.
    """
