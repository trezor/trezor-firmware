from trezor import log, ui, wire
from trezor.crypto import bip32
from trezor.crypto.curve import ed25519
from trezor.messages.CardanoMessageSignature import CardanoMessageSignature

from .address import _break_address_n_to_lines, derive_address_and_node
from .ui import show_swipable_with_confirmation

from apps.common import seed, storage


async def cardano_sign_message(ctx, msg):
    mnemonic = storage.get_mnemonic()
    root_node = bip32.from_mnemonic_cardano(mnemonic)

    try:
        signature = _sign_message(root_node, msg.message, msg.address_n)
    except ValueError as e:
        if __debug__:
            log.exception(__name__, e)
        raise wire.ProcessError("Signing failed")
    mnemonic = None
    root_node = None

    if not await show_swipable_with_confirmation(
        ctx, msg.message, "Signing message", ui.ICON_RECEIVE, ui.GREEN
    ):
        raise wire.ActionCancelled("Signing cancelled")

    if not await show_swipable_with_confirmation(
        ctx,
        _break_address_n_to_lines(msg.address_n),
        "With address",
        ui.ICON_RECEIVE,
        ui.GREEN,
    ):
        raise wire.ActionCancelled("Signing cancelled")

    return signature


def _sign_message(root_node, message: str, derivation_path: list):
    address, node = derive_address_and_node(root_node, derivation_path)

    signature = ed25519.sign_ext(node.private_key(), node.private_key_ext(), message)

    sig = CardanoMessageSignature()
    sig.public_key = seed.remove_ed25519_prefix(node.public_key())
    sig.signature = signature

    return sig
