from ubinascii import hexlify

from trezor import ui, wire
from trezor.messages.GetOwnershipProof import GetOwnershipProof
from trezor.messages.OwnershipProof import OwnershipProof
from trezor.ui.components.tt.text import Text

from apps.common.confirm import require_confirm
from apps.common.paths import validate_path

from . import addresses, common, scripts
from .keychain import validate_path_against_script_type, with_keychain
from .ownership import generate_proof, get_identifier

if False:
    from typing import Optional
    from apps.common.coininfo import CoinInfo
    from apps.common.keychain import Keychain
    from .authorization import CoinJoinAuthorization

# Maximum number of characters per line in monospace font.
_MAX_MONO_LINE = 18


@with_keychain
async def get_ownership_proof(
    ctx: wire.Context,
    msg: GetOwnershipProof,
    keychain: Keychain,
    coin: CoinInfo,
    authorization: Optional[CoinJoinAuthorization] = None,
) -> OwnershipProof:
    if authorization:
        if not authorization.check_get_ownership_proof(msg):
            raise wire.ProcessError("Unauthorized operation")
    else:
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

    node = keychain.derive(msg.address_n)
    address = addresses.get_address(msg.script_type, coin, node, msg.multisig)
    script_pubkey = scripts.output_derive_script(address, coin)
    ownership_id = get_identifier(script_pubkey, keychain)

    # If the scriptPubKey is multisig, then the caller has to provide
    # ownership IDs, otherwise providing an ID is optional.
    if msg.multisig:
        if ownership_id not in msg.ownership_ids:
            raise wire.DataError("Missing ownership identifier")
    elif msg.ownership_ids:
        if msg.ownership_ids != [ownership_id]:
            raise wire.DataError("Invalid ownership identifier")
    else:
        msg.ownership_ids = [ownership_id]

    # In order to set the "user confirmation" bit in the proof, the user must actually confirm.
    if msg.user_confirmation and not authorization:
        text = Text("Proof of ownership", ui.ICON_CONFIG)
        text.normal("Do you want to create a")
        if not msg.commitment_data:
            text.normal("proof of ownership?")
        else:
            hex_data = hexlify(msg.commitment_data).decode()
            text.normal("proof of ownership for:")
            if len(hex_data) > 3 * _MAX_MONO_LINE:
                text.mono(hex_data[0:_MAX_MONO_LINE])
                text.mono(
                    hex_data[_MAX_MONO_LINE : 3 * _MAX_MONO_LINE // 2 - 1]
                    + "..."
                    + hex_data[-3 * _MAX_MONO_LINE // 2 + 2 : -_MAX_MONO_LINE]
                )
                text.mono(hex_data[-_MAX_MONO_LINE:])
            else:
                text.mono(hex_data)

        await require_confirm(ctx, text)

    ownership_proof, signature = generate_proof(
        node,
        msg.script_type,
        msg.multisig,
        coin,
        msg.user_confirmation,
        msg.ownership_ids,
        script_pubkey,
        msg.commitment_data,
    )

    return OwnershipProof(ownership_proof=ownership_proof, signature=signature)
