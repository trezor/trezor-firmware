import gc

from trezor.crypto import beam
from trezor.messages.BeamECCPoint import BeamECCPoint

from apps.common import storage


async def generate_key(ctx, msg):
    gc.collect()

    key_image_x = bytearray(32)
    key_image_y = bytearray(1)

    mnemonic = storage.device.get_mnemonic_secret()
    seed = beam.from_mnemonic_beam(mnemonic)

    beam.generate_key(
        msg.kidv.idx,
        msg.kidv.type,
        msg.kidv.sub_idx,
        msg.kidv.value,
        msg.is_coin_key,
        seed,
        key_image_x,
        key_image_y,
    )

    return BeamECCPoint(x=key_image_x, y=int(key_image_y[0]))
