from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import GetNonce, Nonce


async def get_nonce(msg: GetNonce) -> Nonce:
    from storage import cache
    from trezor.crypto import random
    from trezor.messages import Nonce

    nonce = random.bytes(32)
    cache.set(cache.APP_COMMON_NONCE, nonce)
    return Nonce(nonce=nonce)
