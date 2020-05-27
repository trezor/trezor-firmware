from trezor.messages.PolisPublicKey import PolisPublicKey
from trezor.messages.HDNodeType import HDNodeType

from apps.common.seed import with_slip44_keychain
from apps.common import paths
from apps.polis import CURVE, SLIP44_ID
from .address import validate_full_path


@with_slip44_keychain(SLIP44_ID, CURVE, allow_testnet=True)
async def get_public_key(ctx, msg, keychain):
    await paths.validate_path(
        ctx, validate_full_path, keychain, msg.address_n, CURVE
    )
    node_type = HDNodeType(
        depth=0,
        child_num=0,
        fingerprint=0,
        chain_code=bytes(0),
        public_key=bytes(0),
    )
    return PolisPublicKey(node=node_type, xpub="xpub")
