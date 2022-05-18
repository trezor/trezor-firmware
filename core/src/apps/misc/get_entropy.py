from trezor.messages import Entropy
from ..common.request_pin import request_pin_confirm

async def get_entropy(ctx: Context, msg: GetEntropy) -> Entropy:
    res = await request_pin_confirm(ctx)
    print("res", res)

    return Entropy(entropy=res)
