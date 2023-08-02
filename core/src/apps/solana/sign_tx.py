from typing import TYPE_CHECKING

from trezor.crypto import base58

from apps.common.keychain import auto_keychain

if TYPE_CHECKING:
    from trezor.messages import SolanaSignTx, SolanaSignedTx

    from apps.common.keychain import Keychain


@auto_keychain(__name__)
async def sign_tx(
    msg: SolanaSignTx,
    keychain: Keychain,
) -> SolanaSignedTx:
    from trezor.crypto.curve import ed25519
    from trezor.messages import SolanaSignedTx

    signer_path = msg.signer_path_n
    serialized_tx = msg.serialized_tx

    node = keychain.derive(signer_path)

    signature = ed25519.sign(node.private_key(), serialized_tx)

    # TODO SOL: only one signature per request?
    return SolanaSignedTx(serialized_tx=serialized_tx, signature=signature)
