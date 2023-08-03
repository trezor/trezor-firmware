from typing import TYPE_CHECKING

from apps.common.keychain import with_slip44_keychain

from . import CURVE, PATTERNS, SLIP44_ID

if TYPE_CHECKING:
    from trezor.messages import SolanaSignTx, SolanaSignedTx
    from apps.common.keychain import Keychain


@with_slip44_keychain(*PATTERNS, slip44_id=SLIP44_ID, curve=CURVE)
async def sign_tx(
    msg: SolanaSignTx,
    keychain: Keychain,
) -> SolanaSignedTx:
    from trezor.crypto.curve import ed25519
    from trezor.messages import SolanaSignedTx
    from apps.common import seed
    from .parsing.parse import parse
    from .instructions import handle_instructions
    from trezor.utils import BufferReader

    signer_path = msg.signer_path_n
    serialized_tx = msg.serialized_tx

    node = keychain.derive(signer_path)

    signature = ed25519.sign(node.private_key(), serialized_tx)

    addresses, blockhash, instructions = parse(BufferReader(serialized_tx))

    signer_pub_key = seed.remove_ed25519_prefix(node.public_key())
    await handle_instructions(instructions, signer_pub_key)

    # TODO SOL: final confirmation screen, include blockhash

    # TODO SOL: only one signature per request?
    return SolanaSignedTx(serialized_tx=serialized_tx, signature=signature)
