from trezor import wire
from trezor.crypto import rlp
from trezor.messages.EthereumSignTx import EthereumSignTx
from trezor.messages.EthereumTxRequest import EthereumTxRequest
from trezor.utils import HashWriter

from apps.ethereum import tokens
from apps.ethereum.layout import (
    require_confirm_data,
    require_confirm_fee,
    require_confirm_tx,
)

# maximum supported chain id
MAX_CHAIN_ID = 2147483630


async def ethereum_sign_tx(ctx, msg):
    from trezor.crypto.hashlib import sha3_256

    msg = sanitize(msg)
    check(msg)

    data_total = msg.data_length

    # detect ERC - 20 token
    token = None
    recipient = msg.to
    value = int.from_bytes(msg.value, "big")
    if (
        len(msg.to) == 20
        and len(msg.value) == 0
        and data_total == 68
        and len(msg.data_initial_chunk) == 68
        and msg.data_initial_chunk[:16]
        == b"\xa9\x05\x9c\xbb\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    ):
        token = tokens.token_by_chain_address(msg.chain_id, msg.to)
        recipient = msg.data_initial_chunk[16:36]
        value = int.from_bytes(msg.data_initial_chunk[36:68], "big")

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

    sha = HashWriter(sha3_256)
    sha.extend(rlp.encode_length(total_length, True))  # total length

    if msg.tx_type is not None:
        sha.extend(rlp.encode(msg.tx_type))

    for field in [msg.nonce, msg.gas_price, msg.gas_limit, msg.to, msg.value]:
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

    digest = sha.get_digest(True)  # True -> use keccak mode
    return await send_signature(ctx, msg, digest)


def get_total_length(msg: EthereumSignTx, data_total: int) -> int:
    length = 0
    if msg.tx_type is not None:
        length += rlp.field_length(1, [msg.tx_type])

    for field in [msg.nonce, msg.gas_price, msg.gas_limit, msg.to, msg.value]:
        length += rlp.field_length(len(field), field[:1])

    if msg.chain_id:  # forks replay protection
        if msg.chain_id < 0x100:
            l = 1
        elif msg.chain_id < 0x10000:
            l = 2
        elif msg.chain_id < 0x1000000:
            l = 3
        else:
            l = 4
        length += rlp.field_length(l, [msg.chain_id])
        length += rlp.field_length(0, 0)
        length += rlp.field_length(0, 0)

    length += rlp.field_length(data_total, msg.data_initial_chunk)
    return length


async def send_request_chunk(ctx, data_left: int):
    from trezor.messages.MessageType import EthereumTxAck

    # TODO: layoutProgress ?
    req = EthereumTxRequest()
    if data_left <= 1024:
        req.data_length = data_left
    else:
        req.data_length = 1024

    return await ctx.call(req, EthereumTxAck)


async def send_signature(ctx, msg: EthereumSignTx, digest):
    from trezor.crypto.curve import secp256k1
    from apps.common import seed

    address_n = msg.address_n or ()
    node = await seed.derive_node(ctx, address_n)

    signature = secp256k1.sign(node.private_key(), digest, False)

    req = EthereumTxRequest()
    req.signature_v = signature[0]
    if msg.chain_id:
        req.signature_v += 2 * msg.chain_id + 8

    req.signature_r = signature[1:33]
    req.signature_s = signature[33:]

    return req


def check(msg: EthereumSignTx):
    if msg.tx_type not in [1, 6, None]:
        raise wire.DataError("tx_type out of bounds")

    if msg.chain_id < 0 or msg.chain_id > MAX_CHAIN_ID:
        raise wire.DataError("chain_id out of bounds")

    if msg.data_length > 0:
        if not msg.data_initial_chunk:
            raise wire.DataError("Data length provided, but no initial chunk")
        # Our encoding only supports transactions up to 2^24 bytes. To
        # prevent exceeding the limit we use a stricter limit on data length.
        if msg.data_length > 16000000:
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
    if msg.to == b"":
        if msg.data_length == 0:
            # sending transaction to address 0 (contract creation) without a data field
            return False
    else:
        if len(msg.to) != 20:
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
        msg.to = b""
    if msg.nonce is None:
        msg.nonce = b""
    if msg.chain_id is None:
        msg.chain_id = 0
    return msg
