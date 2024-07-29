from typing import TYPE_CHECKING

from trezor.wire import context

if TYPE_CHECKING:
    from typing import Callable, ParamSpec

    P = ParamSpec("P")
    ByteFunc = Callable[P, bytes]


def stored(key: int) -> Callable[[ByteFunc[P]], ByteFunc[P]]:
    def decorator(func: ByteFunc[P]) -> ByteFunc[P]:
        def wrapper(*args: P.args, **kwargs: P.kwargs):
            value = context.cache_get(key)
            if value is None:
                value = func(*args, **kwargs)
                context.cache_set(key, value)
            return value

        return wrapper

    return decorator
