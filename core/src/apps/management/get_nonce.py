from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import GetNonce, Nonce


async def get_nonce(msg: GetNonce) -> Nonce:
    from storage.cache_common import APP_COMMON_NONCE
    from trezor.crypto import random
    from trezor.messages import Nonce
    from trezor.wire.context import cache_set

    nonce = random.bytes(32)
    cache_set(APP_COMMON_NONCE, nonce)
    return Nonce(nonce=nonce)
