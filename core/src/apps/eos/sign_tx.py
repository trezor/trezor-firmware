from trezor import wire
from trezor.crypto.curve import secp256k1
from trezor.crypto.hashlib import sha256
from trezor.messages import EosSignedTx, EosSignTx, EosTxActionAck, EosTxActionRequest
from trezor.utils import HashWriter

from apps.common import paths
from apps.common.keychain import Keychain, auto_keychain

from . import writers
from .actions import process_action
from .helpers import base58_encode
from .layout import require_sign_tx


@auto_keychain(__name__)
async def sign_tx(ctx: wire.Context, msg: EosSignTx, keychain: Keychain) -> EosSignedTx:
    if msg.chain_id is None:
        raise wire.DataError("No chain id")
    if msg.header is None:
        raise wire.DataError("No header")
    if msg.num_actions is None or msg.num_actions == 0:
        raise wire.DataError("No actions")

    await paths.validate_path(ctx, keychain, msg.address_n)

    node = keychain.derive(msg.address_n)
    sha = HashWriter(sha256())
    await _init(ctx, sha, msg)
    await _actions(ctx, sha, msg.num_actions)
    writers.write_variant32(sha, 0)
    writers.write_bytes_fixed(sha, bytearray(32), 32)

    digest = sha.get_digest()
    signature = secp256k1.sign(
        node.private_key(), digest, True, secp256k1.CANONICAL_SIG_EOS
    )

    return EosSignedTx(signature=base58_encode("SIG_", "K1", signature))


async def _init(ctx: wire.Context, sha: HashWriter, msg: EosSignTx) -> None:
    writers.write_bytes_fixed(sha, msg.chain_id, 32)
    writers.write_header(sha, msg.header)
    writers.write_variant32(sha, 0)
    writers.write_variant32(sha, msg.num_actions)

    await require_sign_tx(ctx, msg.num_actions)


async def _actions(ctx: wire.Context, sha: HashWriter, num_actions: int) -> None:
    for i in range(num_actions):
        action = await ctx.call(EosTxActionRequest(), EosTxActionAck)
        await process_action(ctx, sha, action)
