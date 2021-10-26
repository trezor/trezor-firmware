from trezor import wire
from trezor.crypto import rlp
from trezor.crypto.curve import secp256k1
from trezor.crypto.hashlib import sha3_256
from trezor.messages import EthereumSignTx, EthereumTxAck, EthereumTxRequest
from trezor.utils import HashWriter

from apps.common import paths

from . import tokens
from .helpers import bytes_from_address
from .keychain import with_keychain_from_chain_id
from .layout import (
    require_confirm_data,
    require_confirm_fee,
    require_confirm_tx,
    require_confirm_unknown_token,
)

if False:
    from typing import Tuple

    from apps.common.keychain import Keychain

    from .keychain import EthereumSignTxAny


# Maximum chain_id which returns the full signature_v (which must fit into an uint32).
# chain_ids larger than this will only return one bit and the caller must recalculate
# the full value: v = 2 * chain_id + 35 + v_bit
MAX_CHAIN_ID = (0xFFFF_FFFF - 36) // 2


@with_keychain_from_chain_id
async def sign_tx(
    ctx: wire.Context, msg: EthereumSignTx, keychain: Keychain
) -> EthereumTxRequest:
    check(msg)
    await paths.validate_path(ctx, keychain, msg.address_n)

    # Handle ERC20s
    token, address_bytes, recipient, value = await handle_erc20(ctx, msg)

    data_total = msg.data_length

    await require_confirm_tx(ctx, recipient, value, msg.chain_id, token)
    if token is None and msg.data_length > 0:
        await require_confirm_data(ctx, msg.data_initial_chunk, data_total)

    await require_confirm_fee(
        ctx,
        value,
        int.from_bytes(msg.gas_price, "big"),
        int.from_bytes(msg.gas_limit, "big"),
        msg.chain_id,
        token,
    )

    data = bytearray()
    data += msg.data_initial_chunk
    data_left = data_total - len(msg.data_initial_chunk)

    total_length = get_total_length(msg, data_total)

    sha = HashWriter(sha3_256(keccak=True))
    rlp.write_header(sha, total_length, rlp.LIST_HEADER_BYTE)

    if msg.tx_type is not None:
        rlp.write(sha, msg.tx_type)

    for field in (msg.nonce, msg.gas_price, msg.gas_limit, address_bytes, msg.value):
        rlp.write(sha, field)

    if data_left == 0:
        rlp.write(sha, data)
    else:
        rlp.write_header(sha, data_total, rlp.STRING_HEADER_BYTE, data)
        sha.extend(data)

    while data_left > 0:
        resp = await send_request_chunk(ctx, data_left)
        data_left -= len(resp.data_chunk)
        sha.extend(resp.data_chunk)

    # eip 155 replay protection
    rlp.write(sha, msg.chain_id)
    rlp.write(sha, 0)
    rlp.write(sha, 0)

    digest = sha.get_digest()
    result = sign_digest(msg, keychain, digest)

    return result


async def handle_erc20(
    ctx: wire.Context, msg: EthereumSignTxAny
) -> Tuple[tokens.TokenInfo | None, bytes, bytes, int]:
    token = None
    address_bytes = recipient = bytes_from_address(msg.to)
    value = int.from_bytes(msg.value, "big")
    if (
        len(msg.to) in (40, 42)
        and len(msg.value) == 0
        and msg.data_length == 68
        and len(msg.data_initial_chunk) == 68
        and msg.data_initial_chunk[:16]
        == b"\xa9\x05\x9c\xbb\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    ):
        token = tokens.token_by_chain_address(msg.chain_id, address_bytes)
        recipient = msg.data_initial_chunk[16:36]
        value = int.from_bytes(msg.data_initial_chunk[36:68], "big")

        if token is tokens.UNKNOWN_TOKEN:
            await require_confirm_unknown_token(ctx, address_bytes)

    return token, address_bytes, recipient, value


def get_total_length(msg: EthereumSignTx, data_total: int) -> int:
    length = 0
    if msg.tx_type is not None:
        length += rlp.length(msg.tx_type)

    fields: Tuple[rlp.RLPItem, ...] = (
        msg.nonce,
        msg.gas_price,
        msg.gas_limit,
        bytes_from_address(msg.to),
        msg.value,
        msg.chain_id,
        0,
        0,
    )

    for field in fields:
        length += rlp.length(field)

    length += rlp.header_length(data_total, msg.data_initial_chunk)
    length += data_total

    return length


async def send_request_chunk(ctx: wire.Context, data_left: int) -> EthereumTxAck:
    # TODO: layoutProgress ?
    req = EthereumTxRequest()
    if data_left <= 1024:
        req.data_length = data_left
    else:
        req.data_length = 1024

    return await ctx.call(req, EthereumTxAck)


def sign_digest(
    msg: EthereumSignTx, keychain: Keychain, digest: bytes
) -> EthereumTxRequest:
    node = keychain.derive(msg.address_n)
    signature = secp256k1.sign(
        node.private_key(), digest, False, secp256k1.CANONICAL_SIG_ETHEREUM
    )

    req = EthereumTxRequest()
    req.signature_v = signature[0]
    if msg.chain_id > MAX_CHAIN_ID:
        req.signature_v -= 27
    else:
        req.signature_v += 2 * msg.chain_id + 8

    req.signature_r = signature[1:33]
    req.signature_s = signature[33:]

    return req


def check(msg: EthereumSignTx) -> None:
    if msg.tx_type not in [1, 6, None]:
        raise wire.DataError("tx_type out of bounds")

    if len(msg.gas_price) + len(msg.gas_limit) > 30:
        raise wire.DataError("Fee overflow")

    check_common_fields(msg)


def check_common_fields(msg: EthereumSignTxAny) -> None:
    if msg.data_length > 0:
        if not msg.data_initial_chunk:
            raise wire.DataError("Data length provided, but no initial chunk")
        # Our encoding only supports transactions up to 2^24 bytes. To
        # prevent exceeding the limit we use a stricter limit on data length.
        if msg.data_length > 16_000_000:
            raise wire.DataError("Data length exceeds limit")
        if len(msg.data_initial_chunk) > msg.data_length:
            raise wire.DataError("Invalid size of initial chunk")

    if len(msg.to) not in (0, 40, 42):
        raise wire.DataError("Invalid recipient address")

    if not msg.to and msg.data_length == 0:
        # sending transaction to address 0 (contract creation) without a data field
        raise wire.DataError("Contract creation without data")

    if msg.chain_id == 0:
        raise wire.DataError("Chain ID out of bounds")
