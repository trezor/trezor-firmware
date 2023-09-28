from typing import TYPE_CHECKING

from apps.common.keychain import with_slip44_keychain

from . import CURVE, PATTERNS, SLIP44_ID
from .transaction import Transaction

if TYPE_CHECKING:
    from trezor.messages import SolanaSignTx, SolanaTxSignature
    from apps.common.keychain import Keychain


@with_slip44_keychain(*PATTERNS, slip44_id=SLIP44_ID, curve=CURVE)
async def sign_tx(
    msg: SolanaSignTx,
    keychain: Keychain,
) -> SolanaTxSignature:
    from trezor.crypto.curve import ed25519
    from trezor.messages import SolanaTxSignature
    from trezor.utils import BufferReader

    address_n = msg.address_n
    serialized_tx = msg.serialized_tx

    node = keychain.derive(address_n)

    transaction: Transaction = Transaction(BufferReader(serialized_tx))

    # Show instructions on UI
    await show_instructions(node.public_key(), transaction)

    # signer_pub_key = seed.remove_ed25519_prefix(node.public_key())

    # TODO SOL: final confirmation screen, include blockhash

    # Generate signature
    signature = ed25519.sign(node.private_key(), serialized_tx)

    # TODO SOL: only one signature per request?
    return SolanaTxSignature(signature=signature)


async def show_instructions(public_key: bytes, transaction: Transaction) -> None:
    from apps.common import seed

    num_instructions = len(transaction.instructions)
    for i, instruction in enumerate(transaction.instructions):
        # Check template id. Template id is derived from program.json
        if instruction.ui_identifier == "ui_confirm":
            from .ui import show_confirm

            await show_confirm(
                (num_instructions, i + 1),
                instruction,
                seed.remove_ed25519_prefix(public_key),
            )
        else:
            # TODO SOL: handle other UI templates
            pass
