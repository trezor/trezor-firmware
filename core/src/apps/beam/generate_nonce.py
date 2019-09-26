import gc

from trezor.messages.BeamECCPoint import BeamECCPoint
from trezor.messages.Failure import Failure

from apps.beam.helpers import get_master_nonce_idx
from apps.beam.nonce import calc_nonce_pub, create_nonce, is_master_nonce_created


async def generate_nonce(ctx, msg):
    gc.collect()

    idx = msg.slot
    if idx == get_master_nonce_idx() or idx > 255:
        return Failure(message="Incorrect slot provided")

    if not is_master_nonce_created():
        return Failure(message="Nonce Generator is not initialized")

    _, new_nonce = create_nonce(idx)
    pubkey_x, pubkey_y = calc_nonce_pub(new_nonce)
    return BeamECCPoint(x=pubkey_x, y=int(pubkey_y[0]))
