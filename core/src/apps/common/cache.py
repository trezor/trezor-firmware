from typing import TYPE_CHECKING

from trezor.wire import context

if TYPE_CHECKING:
    from typing import Awaitable, Callable, ParamSpec

    P = ParamSpec("P")
    ByteFunc = Callable[P, bytes]
    AsyncByteFunc = Callable[P, Awaitable[bytes]]


def stored(key: int) -> Callable[[ByteFunc[P]], ByteFunc[P]]:
    """
    Caches the result of a function call based on the given key.

    - If the key is already present in the cache, the cached value is returned
    directly without invoking the decorated function.

    - If the key is not present in the cache, the decorated function is executed,
    and its result is stored in the cache before being returned to the caller.
    """

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
    """
    Caches the result of an async function call based on the given key.

    - If the key is already present in the cache, the cached value is returned
    directly without invoking the decorated asynchronous function.

    - If the key is not present in the cache, the decorated asynchronous function
    is executed, and its result is stored in the cache before being returned
    to the caller.
    """

    def decorator(func: AsyncByteFunc[P]) -> AsyncByteFunc[P]:
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> bytes:
            value = context.cache_get(key)
            if value is None:
                value = await func(*args, **kwargs)
                context.cache_set(key, value)
            return value

        return wrapper

    return decorator
