from trezor import wire
from trezor.crypto import rlp
from trezor.crypto.curve import secp256k1
from trezor.crypto.hashlib import sha3_256
from trezor.messages import EthereumSignTx, EthereumTxAck, EthereumTxRequest
from trezor.utils import HashWriter

from apps.common import paths

from . import address, tokens
from .keychain import with_keychain_from_chain_id
from .layout import (
    require_confirm_data,
    require_confirm_fee,
    require_confirm_tx,
    require_confirm_unknown_token,
)

# maximum supported chain id
MAX_CHAIN_ID = 2147483629


@with_keychain_from_chain_id
async def sign_tx(ctx, msg, keychain):
    msg = sanitize(msg)
    check(msg)
    await paths.validate_path(ctx, keychain, msg.address_n)

    data_total = msg.data_length

    # detect ERC - 20 token
    token = None
    address_bytes = recipient = address.bytes_from_address(msg.to)
    value = int.from_bytes(msg.value, "big")
    if (
        len(msg.to) in (40, 42)
        and len(msg.value) == 0
        and data_total == 68
        and len(msg.data_initial_chunk) == 68
        and msg.data_initial_chunk[:16]
        == b"\xa9\x05\x9c\xbb\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    ):
        token = tokens.token_by_chain_address(msg.chain_id, address_bytes)
        recipient = msg.data_initial_chunk[16:36]
        value = int.from_bytes(msg.data_initial_chunk[36:68], "big")

        if token is tokens.UNKNOWN_TOKEN:
            await require_confirm_unknown_token(ctx, address_bytes)

    await require_confirm_tx(ctx, recipient, value, msg.chain_id, token, msg.tx_type)
    if token is None and msg.data_length > 0:
        await require_confirm_data(ctx, msg.data_initial_chunk, data_total)

    await require_confirm_fee(
        ctx,
        value,
        int.from_bytes(msg.gas_price, "big"),
        int.from_bytes(msg.gas_limit, "big"),
        msg.chain_id,
        token,
        msg.tx_type,
    )

    data = bytearray()
    data += msg.data_initial_chunk
    data_left = data_total - len(msg.data_initial_chunk)

    total_length = get_total_length(msg, data_total)

    sha = HashWriter(sha3_256(keccak=True))
    sha.extend(rlp.encode_length(total_length, True))  # total length

    if msg.tx_type is not None:
        sha.extend(rlp.encode(msg.tx_type))

    for field in (msg.nonce, msg.gas_price, msg.gas_limit, address_bytes, msg.value):
        sha.extend(rlp.encode(field))

    if data_left == 0:
        sha.extend(rlp.encode(data))
    else:
        sha.extend(rlp.encode_length(data_total, False))
        sha.extend(rlp.encode(data, False))

    while data_left > 0:
        resp = await send_request_chunk(ctx, data_left)
        data_left -= len(resp.data_chunk)
        sha.extend(resp.data_chunk)

    # eip 155 replay protection
    if msg.chain_id:
        sha.extend(rlp.encode(msg.chain_id))
        sha.extend(rlp.encode(0))
        sha.extend(rlp.encode(0))

    digest = sha.get_digest()
    result = sign_digest(msg, keychain, digest)

    return result


def get_total_length(msg: EthereumSignTx, data_total: int) -> int:
    length = 0
    if msg.tx_type is not None:
        length += rlp.field_length(1, [msg.tx_type])

    length += rlp.field_length(len(msg.nonce), msg.nonce[:1])
    length += rlp.field_length(len(msg.gas_price), msg.gas_price)
    length += rlp.field_length(len(msg.gas_limit), msg.gas_limit)
    to = address.bytes_from_address(msg.to)
    length += rlp.field_length(len(to), to)
    length += rlp.field_length(len(msg.value), msg.value)

    if msg.chain_id:  # forks replay protection
        if msg.chain_id < 0x100:
            l = 1
        elif msg.chain_id < 0x1_0000:
            l = 2
        elif msg.chain_id < 0x100_0000:
            l = 3
        else:
            l = 4
        length += rlp.field_length(l, [msg.chain_id])
        length += rlp.field_length(0, 0)
        length += rlp.field_length(0, 0)

    length += rlp.field_length(data_total, msg.data_initial_chunk)
    return length


async def send_request_chunk(ctx, data_left: int):
    # TODO: layoutProgress ?
    req = EthereumTxRequest()
    if data_left <= 1024:
        req.data_length = data_left
    else:
        req.data_length = 1024

    return await ctx.call(req, EthereumTxAck)


def sign_digest(msg: EthereumSignTx, keychain, digest):
    node = keychain.derive(msg.address_n)
    signature = secp256k1.sign(
        node.private_key(), digest, False, secp256k1.CANONICAL_SIG_ETHEREUM
    )

    req = EthereumTxRequest()
    req.signature_v = signature[0]
    if msg.chain_id > MAX_CHAIN_ID:
        req.signature_v -= 27
    elif msg.chain_id:
        req.signature_v += 2 * msg.chain_id + 8

    req.signature_r = signature[1:33]
    req.signature_s = signature[33:]

    return req


def check(msg: EthereumSignTx):
    if msg.tx_type not in [1, 6, None]:
        raise wire.DataError("tx_type out of bounds")

    if msg.chain_id < 0:
        raise wire.DataError("chain_id out of bounds")

    if msg.data_length > 0:
        if not msg.data_initial_chunk:
            raise wire.DataError("Data length provided, but no initial chunk")
        # Our encoding only supports transactions up to 2^24 bytes. To
        # prevent exceeding the limit we use a stricter limit on data length.
        if msg.data_length > 16_000_000:
            raise wire.DataError("Data length exceeds limit")
        if len(msg.data_initial_chunk) > msg.data_length:
            raise wire.DataError("Invalid size of initial chunk")

    # safety checks
    if not check_gas(msg) or not check_to(msg):
        raise wire.DataError("Safety check failed")


def check_gas(msg: EthereumSignTx) -> bool:
    if msg.gas_price is None or msg.gas_limit is None:
        return False
    if len(msg.gas_price) + len(msg.gas_limit) > 30:
        # sanity check that fee doesn't overflow
        return False
    return True


def check_to(msg: EthereumTxRequest) -> bool:
    if msg.to == "":
        if msg.data_length == 0:
            # sending transaction to address 0 (contract creation) without a data field
            return False
    else:
        if len(msg.to) not in (40, 42):
            return False
    return True


def sanitize(msg):
    if msg.value is None:
        msg.value = b""
    if msg.data_initial_chunk is None:
        msg.data_initial_chunk = b""
    if msg.data_length is None:
        msg.data_length = 0
    if msg.to is None:
        msg.to = ""
    if msg.nonce is None:
        msg.nonce = b""
    if msg.chain_id is None:
        msg.chain_id = 0
    return msg
