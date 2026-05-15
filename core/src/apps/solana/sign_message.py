from typing import TYPE_CHECKING

from apps.common.keychain import with_slip44_keychain

from . import CURVE, PATTERNS, SLIP44_ID

if TYPE_CHECKING:
    from trezor.messages import SolanaMessageSignature, SolanaSignMessage

    from apps.common.keychain import Keychain


@with_slip44_keychain(*PATTERNS, slip44_id=SLIP44_ID, curve=CURVE)
async def sign_message(
    msg: SolanaSignMessage, keychain: Keychain
) -> SolanaMessageSignature:
    from trezor.crypto.curve import ed25519
    from trezor.messages import SolanaMessageSignature
    from trezor.wire import DataError

    from apps.common import seed

    from .layout import confirm_offchain_signverify
    from .offchain_message import OffchainMessage

    offchain_message = OffchainMessage.from_bytes(msg.message)

    node = keychain.derive(msg.address_n)
    public_key = seed.remove_ed25519_prefix(node.public_key())

    if public_key not in offchain_message.signers:
        raise DataError("Requested key not among signers")
    signer_index = offchain_message.signers.index(public_key)

    await confirm_offchain_signverify(
        offchain_message,
        verify=False,
        signer_index=signer_index,
        signer_path=msg.address_n,
        chunkify=bool(msg.chunkify),
    )

    signature = ed25519.sign(node.private_key(), msg.message)
    return SolanaMessageSignature(signature=signature)
