from typing import TYPE_CHECKING

from trezor.wire import context

if TYPE_CHECKING:
    from typing import Awaitable, Callable, ParamSpec

    P = ParamSpec("P")
    ByteFunc = Callable[P, bytes]
    AsyncByteFunc = Callable[P, Awaitable[bytes]]


def stored(key: int) -> Callable[[ByteFunc[P]], ByteFunc[P]]:
    def decorator(func: ByteFunc[P]) -> ByteFunc[P]:

        def wrapper(*args: P.args, **kwargs: P.kwargs) -> bytes:
            value = context.cache_get(key)
            if value is None:
                value = func(*args, **kwargs)
                context.cache_set(key, value)
            return value

        return wrapper

    return decorator


def stored_async(key: int) -> Callable[[AsyncByteFunc[P]], AsyncByteFunc[P]]:
    def decorator(func: AsyncByteFunc[P]) -> AsyncByteFunc[P]:
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> bytes:
            value = context.cache_get(key)
            if value is None:
                value = await func(*args, **kwargs)
                context.cache_set(key, value)
            return value

        return wrapper

    return decorator
