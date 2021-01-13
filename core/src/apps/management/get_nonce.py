from micropython import const

from storage import cache
from trezor import wire
from trezor.crypto import random
from trezor.messages.GetNonce import GetNonce
from trezor.messages.Nonce import Nonce

if False:
    from typing import List

_MAX_NONCES_COUNT = const(10)


async def get_nonce(ctx: wire.Context, msg: GetNonce) -> Nonce:
    nonce = random.bytes(32)
    nonces: List[bytes] = cache.get(cache.APP_COMMON_NONCES)
    if not nonces:
        nonces = []
        cache.set(cache.APP_COMMON_NONCES, nonces)
    elif len(nonces) >= _MAX_NONCES_COUNT:
        nonces.pop()

    nonces.insert(0, nonce)
    return Nonce(nonce=nonce)
