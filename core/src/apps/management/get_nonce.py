from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import GetNonce, Nonce
    from trezor.wire import Context


async def get_nonce(ctx: Context, msg: GetNonce) -> Nonce:
    from trezor.crypto import random
    from trezor.messages import Nonce

    from storage import cache

    nonce = random.bytes(32)
    cache.set(cache.APP_COMMON_NONCE, nonce)
    return Nonce(nonce=nonce)
