from trezor.messages.PolisAddress import PolisAddress

from apps.common.seed import with_slip44_keychain
from apps.common import paths
from apps.polis import CURVE, SLIP44_ID
from .address import validate_full_path


@with_slip44_keychain(SLIP44_ID, CURVE, allow_testnet=True)
async def get_address(ctx, msg, keychain):
    await paths.validate_path(ctx, validate_full_path, keychain, msg.address_n, CURVE)
    return PolisAddress(address="address")
