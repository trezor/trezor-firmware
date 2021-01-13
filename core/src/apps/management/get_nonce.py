from storage import cache
from trezor import wire
from trezor.crypto import random
from trezor.messages.GetNonce import GetNonce
from trezor.messages.Nonce import Nonce

if False:
    from typing import Set


async def get_nonce(ctx: wire.Context, msg: GetNonce) -> Nonce:
    nonce = random.bytes(32)
    nonces: Set[bytes] = cache.get(cache.APP_COMMON_NONCES)
    if not nonces:
        nonces = set()
        cache.set(cache.APP_COMMON_NONCES, nonces)

    nonces.add(nonce)
    return Nonce(nonce=nonce)
