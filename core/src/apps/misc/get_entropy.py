from trezor.messages import Entropy
from trezor.ui.layouts import request_pin_on_device

async def get_entropy(ctx: Context, msg: GetEntropy) -> Entropy:
    res = await request_pin_on_device(ctx, "Give me PIN", 4, True)
    print("res", res)

    return Entropy(entropy=res)