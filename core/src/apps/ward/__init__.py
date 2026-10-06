from micropython import const
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from enum import IntEnum
    from typing import Any, TypeVar

    from .store import WardStore

    T = TypeVar("T")
    HandlerWithWard = Callable[..., Awaitable[T]]
else:
    IntEnum = int


class WardApp(IntEnum):
    """Apps using WARD.

    The ids are persisted in the records, never renumber or reuse them.
    """

    BITCOIN = const(1)


async def open_ward(app: WardApp) -> WardStore:
    """Open the WARD store of `app` in the current passphrase wallet."""
    from .keys import derive_wallet_id
    from .store import WardStore

    return WardStore(await derive_wallet_id(), bytes([app]))


def with_ward(app: WardApp) -> Callable[[HandlerWithWard[T]], HandlerWithWard[T]]:
    """Pass the WARD store of `app` to the handler as the `ward` keyword argument.

    Must be the innermost decorator: the keychain decorators call the handler
    with a fixed set of positional arguments and do not forward keyword
    arguments. Positional arguments are passed through unchanged (e.g.
    `msg, keychain, coin` from the bitcoin `with_keychain`).
    """

    def decorator(func: HandlerWithWard[T]) -> HandlerWithWard[T]:
        async def wrapper(*args: Any) -> T:
            from trezor.wire import ProcessError

            from .store import WardError

            ward = await open_ward(app)
            try:
                return await func(*args, ward=ward)
            except WardError:
                raise ProcessError("WARD error")

        return wrapper

    return decorator
