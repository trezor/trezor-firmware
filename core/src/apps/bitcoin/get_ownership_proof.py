from typing import TYPE_CHECKING

from .keychain import with_keychain

if TYPE_CHECKING:
    from trezor.messages import GetOwnershipProof, OwnershipProof

    from apps.common.coininfo import CoinInfo
    from apps.common.keychain import Keychain

    from .authorization import CoinJoinAuthorization


@with_keychain
async def get_ownership_proof(
    msg: GetOwnershipProof,
    keychain: Keychain,
    coin: CoinInfo,
    authorization: CoinJoinAuthorization | None = None,
) -> OwnershipProof:
    from trezor.enums import InputScriptType
    from trezor.messages import OwnershipProof
    from trezor.ui.layouts import confirm_action, confirm_blob
    from trezor.wire import DataError, ProcessError

    from apps.common.paths import validate_path

    from . import addresses, common, scripts
    from .keychain import validate_path_against_script_type
    from .ownership import generate_proof, get_identifier

    script_type = msg.script_type  # local_cache_attribute
    ownership_ids = msg.ownership_ids  # local_cache_attribute

    if authorization:
        if not authorization.check_get_ownership_proof(msg):
            raise ProcessError("Unauthorized operation")
    else:
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

    # If the scriptPubKey is multisig, then the caller has to provide
    # ownership IDs, otherwise providing an ID is optional.
    if msg.multisig:
        if ownership_id not in ownership_ids:
            raise DataError("Missing ownership identifier")
    elif ownership_ids:
        if ownership_ids != [ownership_id]:
            raise DataError("Invalid ownership identifier")
    else:
        ownership_ids = [ownership_id]

    # In order to set the "user confirmation" bit in the proof, the user must actually confirm.
    if msg.user_confirmation and not authorization:
        await confirm_action(
            "confirm_ownership_proof",
            "Proof of ownership",
            description="Do you want to create a proof of ownership?",
        )
        if msg.commitment_data:
            await confirm_blob(
                "confirm_ownership_proof",
                "Proof of ownership",
                msg.commitment_data,
                "Commitment data:",
            )

    ownership_proof, signature = generate_proof(
        node,
        script_type,
        msg.multisig,
        coin,
        msg.user_confirmation,
        ownership_ids,
        script_pubkey,
        msg.commitment_data,
    )

    return OwnershipProof(ownership_proof=ownership_proof, signature=signature)
