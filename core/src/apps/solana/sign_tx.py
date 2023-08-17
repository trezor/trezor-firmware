from typing import TYPE_CHECKING

from apps.common.keychain import with_slip44_keychain

from . import CURVE, PATTERNS, SLIP44_ID

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
    from apps.common import seed
    from .parser_poc import parser
    from .parser_poc import builder
    from .parsing.parse import parse
    from .instructions import handle_instructions
    from trezor.utils import BufferReader

    address_n = msg.address_n
    serialized_tx = msg.serialized_tx

    node = keychain.derive(address_n)

    signature = ed25519.sign(node.private_key(), serialized_tx)
    signer_pub_key = seed.remove_ed25519_prefix(node.public_key())

    parsed_msg = parser.parse_message(BufferReader(serialized_tx))
    print(parsed_msg)

    await builder.show_parsed_message(parsed_msg)

    return SolanaTxSignature(signature=signature)

    # TODO Gabo's original code

    # address_n = msg.address_n
    # serialized_tx = msg.serialized_tx

    # node = keychain.derive(address_n)

    # signature = ed25519.sign(node.private_key(), serialized_tx)

    # _, _, instructions = parse(BufferReader(serialized_tx))

    # signer_pub_key = seed.remove_ed25519_prefix(node.public_key())
    # await handle_instructions(instructions, signer_pub_key)

    # # TODO SOL: final confirmation screen, include blockhash

    # # TODO SOL: only one signature per request?
    # return SolanaTxSignature(signature=signature)
