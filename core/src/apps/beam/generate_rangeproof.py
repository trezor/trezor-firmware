import gc

from trezor.crypto import beam
from trezor.messages.BeamRangeproofData import BeamRangeproofData

from apps.common import storage


async def generate_rangeproof(ctx, msg):
    gc.collect()

    asset_id = bytearray(0)
    rangeproof_data = bytearray(688)

    mnemonic = storage.device.get_mnemonic_secret()
    seed = beam.from_mnemonic_beam(mnemonic)

    beam.generate_rp_from_key_idv(
        msg.kidv.idx,
        msg.kidv.type,
        msg.kidv.sub_idx,
        msg.kidv.value,
        asset_id,
        msg.is_public,
        seed,
        rangeproof_data,
    )

    return BeamRangeproofData(data=rangeproof_data, is_public=msg.is_public)
