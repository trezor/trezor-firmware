from trezor import wire
from trezor.enums import InputScriptType
from trezor.messages import GetOwnershipId, OwnershipId

from apps.common.paths import validate_path

from . import addresses, common, scripts
from .keychain import validate_path_against_script_type, with_keychain
from .ownership import get_identifier

if False:
    from apps.common.coininfo import CoinInfo
    from apps.common.keychain import Keychain


@with_keychain
async def get_ownership_id(
    ctx: wire.Context, msg: GetOwnershipId, keychain: Keychain, coin: CoinInfo
) -> OwnershipId:
    await validate_path(
        ctx,
        keychain,
        msg.address_n,
        validate_path_against_script_type(coin, msg),
    )

    if msg.script_type not in common.INTERNAL_INPUT_SCRIPT_TYPES:
        raise wire.DataError("Invalid script type")

    if msg.script_type in common.SEGWIT_INPUT_SCRIPT_TYPES and not coin.segwit:
        raise wire.DataError("Segwit not enabled on this coin")

    if msg.script_type == InputScriptType.SPENDTAPROOT and not coin.taproot:
        raise wire.DataError("Taproot not enabled on this coin")

    node = keychain.derive(msg.address_n)
    address = addresses.get_address(msg.script_type, coin, node, msg.multisig)
    script_pubkey = scripts.output_derive_script(address, coin)
    ownership_id = get_identifier(script_pubkey, keychain)

    return OwnershipId(ownership_id=ownership_id)
