import gc
import ubinascii

from trezor.crypto import beam
from trezor.messages.BeamOwnerKey import BeamOwnerKey

from apps.beam.helpers import get_beam_kdf, rand_pswd
from apps.beam.layout import beam_confirm_message


async def get_owner_key(ctx, msg):
    gc.collect()

    export_warning_msg = (
        "Exposing the key to a third party allows them to see your balance."
    )
    await beam_confirm_message(ctx, "Owner key", export_warning_msg, False)
    wait_warning_msg = "Please wait few seconds until exporting is done"
    await beam_confirm_message(ctx, "Owner key", wait_warning_msg, False)

    pswd = rand_pswd()
    owner_key = generate_owner_key(pswd)

    if msg.show_display:
        await beam_confirm_message(
            ctx, "Owner key", owner_key[:32] + " ... " + owner_key[-32:], True
        )

    await beam_confirm_message(ctx, "Key Password", pswd, False)

    return BeamOwnerKey(key=owner_key)


def generate_owner_key(passphrase, mnemonic=None):
    owner_key = bytearray(108)
    master_secret, master_cofactor = get_beam_kdf(mnemonic)
    beam.export_owner_key(
        master_secret, master_cofactor, passphrase, len(passphrase), owner_key
    )
    owner_key = ubinascii.b2a_base64(owner_key)

    return owner_key
