import gc

from trezor.messages import ButtonRequestType
from trezor.messages.BeamECCPoint import BeamECCPoint

from apps.beam.helpers import get_beam_pk
from apps.beam.layout import beam_confirm_message


async def get_public_key(ctx, msg):
    gc.collect()

    pubkey_x, pubkey_y = get_beam_pk(msg.kid_idx, msg.kid_sub_idx)

    if msg.show_display:
        await beam_confirm_message(
            ctx, "Confirm public key X", pubkey_x, True, ButtonRequestType.PublicKey
        )
    if msg.show_display:
        await beam_confirm_message(
            ctx,
            "Confirm public key Y",
            str(pubkey_y),
            False,
            ButtonRequestType.PublicKey,
        )

    return BeamECCPoint(x=pubkey_x, y=pubkey_y)
