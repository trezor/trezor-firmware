from typing import TYPE_CHECKING

from .keychain import with_keychain

if TYPE_CHECKING:
    from trezor.messages import GetOwnershipId, OwnershipId

    from apps.common.coininfo import CoinInfo
    from apps.common.keychain import Keychain


@with_keychain
async def get_ownership_id(
    msg: GetOwnershipId, keychain: Keychain, coin: CoinInfo
) -> OwnershipId:
    from trezor.enums import InputScriptType
    from trezor.messages import OwnershipId
    from trezor.wire import DataError

    from apps.common.paths import validate_path

    from . import addresses, common, scripts
    from .keychain import validate_path_against_script_type
    from .ownership import get_identifier

    script_type = msg.script_type  # local_cache_attribute

    await validate_path(
        keychain,
        msg.address_n,
        validate_path_against_script_type(coin, msg),
    )

    if script_type not in common.INTERNAL_INPUT_SCRIPT_TYPES:
        raise DataError("Invalid script type")

    if script_type in common.SEGWIT_INPUT_SCRIPT_TYPES and not coin.segwit:
        raise DataError("Segwit not enabled on this coin")

    if script_type == InputScriptType.SPENDTAPROOT and not coin.taproot:
        raise DataError("Taproot not enabled on this coin")

    node = keychain.derive(msg.address_n)
    address = addresses.get_address(script_type, coin, node, msg.multisig)
    script_pubkey = scripts.output_derive_script(address, coin)
    ownership_id = get_identifier(script_pubkey, keychain)

    return OwnershipId(ownership_id=ownership_id)
