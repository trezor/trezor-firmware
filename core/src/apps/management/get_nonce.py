from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import GetNonce, Nonce


async def get_nonce(msg: GetNonce) -> Nonce:
    from storage.cache_common import APP_COMMON_NONCE
    from trezor.crypto import random
    from trezor.messages import Nonce
    from trezor.wire import context

    nonce = random.bytes(32)
    context.cache_set(APP_COMMON_NONCE, nonce)
    return Nonce(nonce=nonce)
