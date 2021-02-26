from trezor import wire
from trezor.crypto import base58
from trezor.crypto.curve import ed25519
from trezor.messages.SolanaSignedTx import SolanaSignedTx

from apps.common import paths
from apps.common.keychain import auto_keychain

from trezor.messages import ButtonRequestType
from trezor import ui
from trezor.ui.components.tt.text import Text

from apps.common.confirm import require_confirm


@auto_keychain(__name__)
async def sign_tx_hash(ctx, msg, keychain):
    await paths.validate_path(ctx, keychain, msg.address_n)

    hash = bytes(msg.hash)

    # Confirm
    text = Text("Sign transaction hash", ui.ICON_SEND, ui.GREEN)
    text.mono(base58.encode(hash))
    await require_confirm(ctx, text, ButtonRequestType.SignTx)

    # Get key
    node = keychain.derive(msg.address_n)
    seckey = node.private_key()
    pubkey = node.public_key()[1:] # skip ed25519 pubkey marker

    # Sign hash
    signature = ed25519.sign(seckey, hash)

    return SolanaSignedTx(signature=signature)


def _get_keys(keychain, msg):
    node = keychain.derive(msg.address_n)

    seckey = node.private_key()
    pubkey = node.public_key()
    pubkey = pubkey[1:]  # skip ed25519 pubkey marker

    return pubkey, seckey
