from micropython import const
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from typing import Any, TypeVar

    from .store import WardStore

    T = TypeVar("T")
    HandlerWithWard = Callable[..., Awaitable[T]]


class WardApp:
    """Apps using WARD.

    The ids are persisted in the records, never renumber or reuse them.
    """

    BITCOIN = const(1)


async def open_ward(app: int) -> WardStore:
    """Open the WARD store of `app` in the current passphrase wallet."""
    raise NotImplementedError


def with_ward(app: int) -> Callable[[HandlerWithWard[T]], HandlerWithWard[T]]:
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
            except WardError as e:
                raise ProcessError(f"WARD: {e}")

        return wrapper

    return decorator
