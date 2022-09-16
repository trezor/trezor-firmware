from typing import TYPE_CHECKING

from apps.common.keychain import auto_keychain

if TYPE_CHECKING:
    from trezor.messages import BinanceSignTx, BinanceSignedTx
    from apps.common.keychain import Keychain
    from trezor.wire import Context


@auto_keychain(__name__)
async def sign_tx(
    ctx: Context, envelope: BinanceSignTx, keychain: Keychain
) -> BinanceSignedTx:
    from trezor import wire
    from trezor.crypto.curve import secp256k1
    from trezor.crypto.hashlib import sha256
    from trezor.enums import MessageType
    from trezor.messages import (
        BinanceCancelMsg,
        BinanceOrderMsg,
        BinanceSignedTx,
        BinanceTransferMsg,
        BinanceTxRequest,
    )

    from apps.common import paths

    from . import helpers, layout

    # create transaction message -> sign it -> create signature/pubkey message -> serialize all
    if envelope.msg_count > 1:
        raise wire.DataError("Multiple messages not supported.")

    await paths.validate_path(ctx, keychain, envelope.address_n)
    node = keychain.derive(envelope.address_n)

    tx_req = BinanceTxRequest()

    msg = await ctx.call_any(
        tx_req,
        MessageType.BinanceCancelMsg,
        MessageType.BinanceOrderMsg,
        MessageType.BinanceTransferMsg,
    )

    if envelope.source < 0:
        raise wire.DataError("Source is invalid.")

    msg_json = helpers.produce_json_for_signing(envelope, msg)

    if BinanceTransferMsg.is_type_of(msg):
        await layout.require_confirm_transfer(ctx, msg)
    elif BinanceOrderMsg.is_type_of(msg):
        await layout.require_confirm_order(ctx, msg)
    elif BinanceCancelMsg.is_type_of(msg):
        await layout.require_confirm_cancel(ctx, msg)
    else:
        raise wire.ProcessError("input message unrecognized")

    # generate_content_signature
    msghash = sha256(msg_json.encode()).digest()
    signature_bytes = secp256k1.sign(node.private_key(), msghash)[1:65]

    return BinanceSignedTx(signature=signature_bytes, public_key=node.public_key())
