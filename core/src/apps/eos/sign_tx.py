from typing import TYPE_CHECKING

from apps.common.keychain import auto_keychain

if TYPE_CHECKING:
    from trezor.messages import EosSignedTx, EosSignTx
    from trezor.wire import Context

    from apps.common.keychain import Keychain


@auto_keychain(__name__)
async def sign_tx(ctx: Context, msg: EosSignTx, keychain: Keychain) -> EosSignedTx:
    from trezor.crypto.curve import secp256k1
    from trezor.crypto.hashlib import sha256
    from trezor.messages import EosSignedTx, EosTxActionAck, EosTxActionRequest
    from trezor.utils import HashWriter
    from trezor.wire import DataError

    from apps.common import paths

    from .actions import process_action
    from .helpers import base58_encode
    from .layout import require_sign_tx
    from .writers import write_bytes_fixed, write_header, write_uvarint

    num_actions = msg.num_actions  # local_cache_attribute

    if not num_actions:
        raise DataError("No actions")

    await paths.validate_path(ctx, keychain, msg.address_n)

    node = keychain.derive(msg.address_n)
    sha = HashWriter(sha256())

    # init
    write_bytes_fixed(sha, msg.chain_id, 32)
    write_header(sha, msg.header)
    write_uvarint(sha, 0)
    write_uvarint(sha, num_actions)
    await require_sign_tx(ctx, num_actions)

    # actions
    for index in range(num_actions):
        action = await ctx.call(EosTxActionRequest(), EosTxActionAck)
        is_last = index == num_actions - 1
        await process_action(ctx, sha, action, is_last)

    write_uvarint(sha, 0)
    write_bytes_fixed(sha, bytearray(32), 32)

    digest = sha.get_digest()
    signature = secp256k1.sign(
        node.private_key(), digest, True, secp256k1.CANONICAL_SIG_EOS
    )

    return EosSignedTx(signature=base58_encode("SIG_", "K1", signature))
