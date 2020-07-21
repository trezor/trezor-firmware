from trezor import wire
from trezor.crypto.curve import secp256k1
from trezor.crypto.hashlib import sha256
from trezor.messages.EosSignedTx import EosSignedTx
from trezor.messages.EosSignTx import EosSignTx
from trezor.messages.EosTxActionAck import EosTxActionAck
from trezor.messages.EosTxActionRequest import EosTxActionRequest
from trezor.utils import HashWriter

from apps.common import paths
from apps.common.keychain import Keychain, with_slip44_keychain
from apps.eos import CURVE, SLIP44_ID, writers
from apps.eos.actions import process_action
from apps.eos.helpers import base58_encode, validate_full_path
from apps.eos.layout import require_sign_tx


@with_slip44_keychain(SLIP44_ID, CURVE)
async def sign_tx(ctx: wire.Context, msg: EosSignTx, keychain: Keychain) -> EosSignedTx:
    if msg.chain_id is None:
        raise wire.DataError("No chain id")
    if msg.header is None:
        raise wire.DataError("No header")
    if msg.num_actions is None or msg.num_actions == 0:
        raise wire.DataError("No actions")

    await paths.validate_path(ctx, validate_full_path, keychain, msg.address_n, CURVE)

    node = keychain.derive(msg.address_n)
    sha = HashWriter(sha256())
    await _init(ctx, sha, msg)
    await _actions(ctx, sha, msg.num_actions)
    writers.write_variant32(sha, 0)
    writers.write_bytes_unchecked(sha, bytearray(32))

    digest = sha.get_digest()
    signature = secp256k1.sign(
        node.private_key(), digest, True, secp256k1.CANONICAL_SIG_EOS
    )

    return EosSignedTx(signature=base58_encode("SIG_", "K1", signature))


async def _init(ctx: wire.Context, sha: HashWriter, msg: EosSignTx) -> None:
    writers.write_bytes_unchecked(sha, msg.chain_id)
    writers.write_header(sha, msg.header)
    writers.write_variant32(sha, 0)
    writers.write_variant32(sha, msg.num_actions)

    await require_sign_tx(ctx, msg.num_actions)


async def _actions(ctx: wire.Context, sha: HashWriter, num_actions: int) -> None:
    for i in range(num_actions):
        action = await ctx.call(EosTxActionRequest(), EosTxActionAck)
        await process_action(ctx, sha, action)
