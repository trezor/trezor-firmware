from storage import cache
from trezor import wire
from trezor.crypto import random
from trezor.messages import GetNonce, Nonce


async def get_nonce(ctx: wire.Context, msg: GetNonce) -> Nonce:
    nonce = random.bytes(32)
    cache.set(cache.APP_COMMON_NONCE, nonce)
    return Nonce(nonce=nonce)
