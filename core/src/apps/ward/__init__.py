from micropython import const
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from typing import Any, TypeVar

    from typing_extensions import Self

    from .store import WardStore

    T = TypeVar("T")
    HandlerWithWard = Callable[..., Awaitable[T]]


class WardApp:
    """Apps using WARD.

    The ids are persisted in the records, never renumber or reuse them.
    """

    BITCOIN = const(1)


class WardField:
    """A key or a value stored in WARD."""

    @classmethod
    def from_bytes(cls, data: bytes) -> Self:
        """Deserialize the field, raise ValueError if `data` is malformed."""
        raise NotImplementedError

    def to_bytes(self) -> bytes:
        """Serialize the field."""
        raise NotImplementedError

    def format(self) -> str:
        """Describe the field to the user."""
        raise NotImplementedError


class WardSchema:
    """The types of the keys and values an app stores in WARD.

    The type ids are persisted in the records, never renumber or reuse them.
    """

    def __init__(self, app: int, types: dict[int, type[WardField]]) -> None:
        self.app = app
        self.types = types
        self.ids: dict[type[WardField], int] = {}
        for type_id, field_type in types.items():
            if not 0 <= type_id <= 0xFF or field_type in self.ids:
                raise ValueError("Invalid WARD schema")
            self.ids[field_type] = type_id


async def open_ward(schema: WardSchema) -> WardStore:
    """Open the WARD store of `schema.app` in the current passphrase wallet."""
    from .keys import derive_wallet_id
    from .store import WardStore

    return WardStore(await derive_wallet_id(), schema)


def with_ward(
    schema: WardSchema,
) -> Callable[[HandlerWithWard[T]], HandlerWithWard[T]]:
    """Pass the WARD store of `schema.app` to the handler as the `ward` keyword argument.

    Must be the innermost decorator: the keychain decorators call the handler
    with a fixed set of positional arguments and do not forward keyword
    arguments. Positional arguments are passed through unchanged (e.g.
    `msg, keychain, coin` from the bitcoin `with_keychain`).
    """

    def decorator(func: HandlerWithWard[T]) -> HandlerWithWard[T]:
        async def wrapper(*args: Any) -> T:
            from trezor.wire import ProcessError

            from .store import WardError

            ward = await open_ward(schema)
            try:
                return await func(*args, ward=ward)
            except WardError as e:
                raise ProcessError(f"WARD: {e}")

        return wrapper

    return decorator
