from trezor.utils import unimport
from trezor.messages.EthereumSignTx import EthereumSignTx
from trezor.messages.EthereumTxRequest import EthereumTxRequest
from trezor.messages import FailureType
from apps.common.hash_writer import HashWriter
from trezor.crypto import rlp
from apps.ethereum import tokens, layout

# maximum supported chain id
MAX_CHAIN_ID = 2147483630


@unimport
async def ethereum_sign_tx(ctx, msg):
    from trezor.crypto.hashlib import sha3_256

    msg = sanitize(msg)
    check(msg)

    data_total = msg.data_length

    # detect ERC - 20 token
    token = None
    if len(msg.to) == 20 and \
       len(msg.value) == 0 and \
       data_total == 68 and \
       len(msg.data_initial_chunk) == 68 and \
       msg.data_initial_chunk[:16] == b'\xa9\x05\x9c\xbb\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00':
        token = tokens.token_by_chain_address(msg.chain_id, msg.to)

    if token is None:
        await layout.confirm_tx(ctx, msg.to, msg.value, msg.chain_id, token)
    else:
        await layout.confirm_tx(ctx, msg.data_initial_chunk[16:36],  msg.data_initial_chunk.bytes[36:68], msg.chain_id, token)

    if token is None and msg.data_length > 0:
        await layout.confirm_data(ctx, msg.data_initial_chunk, data_total)

    await layout.confirm_fee(ctx, msg.value, msg.gas_price, msg.gas_limit, msg.chain_id, token)

    data = bytearray()
    data += msg.data_initial_chunk
    data_left = data_total - len(msg.data_initial_chunk)

    total_length = get_total_length(msg, data_total)

    sha = HashWriter(sha3_256)
    sha.extend(rlp.encode_length(total_length, True))  # total length

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
    for field in [msg.nonce, msg.gas_price, msg.gas_limit, msg.to, msg.value]:
        length += rlp.field_length(len(field), field[:1])

    if msg.chain_id:  # forks replay protection
        length += rlp.field_length(1, [msg.chain_id])
        length += rlp.field_length(0, 0)
        length += rlp.field_length(0, 0)

    length += rlp.field_length(data_total, msg.data_initial_chunk)
    return length


async def send_request_chunk(ctx, data_left: int):
    from trezor.messages.wire_types import EthereumTxAck
    # todo layoutProgress ?
    req = EthereumTxRequest()
    if data_left <= 1024:
        req.data_length = data_left
    else:
        req.data_length = 1024

    return await ctx.call(req, EthereumTxAck)


async def send_signature(ctx, msg: EthereumSignTx, digest):
    from trezor.crypto.curve import secp256k1
    from ..common import seed

    address_n = msg.address_n or ()
    node = await seed.get_root(ctx)
    node.derive_path(address_n)

    signature = secp256k1.sign(node.private_key(), digest, False)

    req = EthereumTxRequest()
    req.signature_v = signature[0]
    if msg.chain_id:
        req.signature_v += 2 * msg.chain_id + 8

    req.signature_r = signature[1:33]
    req.signature_s = signature[33:]

    return req


def node_derive(root, address_n: list):
    node = root.clone()
    node.derive_path(address_n)
    return node


def check(msg: EthereumSignTx):
    if msg.chain_id < 0 or msg.chain_id > MAX_CHAIN_ID:
        raise ValueError(FailureType.DataError, 'Chain id out of bounds')

    if msg.data_length > 0:
        if not msg.data_initial_chunk:
            raise ValueError(FailureType.DataError, 'Data length provided, but no initial chunk')
        # Our encoding only supports transactions up to 2^24 bytes. To
        # prevent exceeding the limit we use a stricter limit on data length.
        if msg.data_length > 16000000:
            raise ValueError(FailureType.DataError, 'Data length exceeds limit')
        if len(msg.data_initial_chunk) > msg.data_length:
            raise ValueError(FailureType.DataError, 'Invalid size of initial chunk')

    # safety checks
    if not check_gas(msg) or not check_to(msg):
        raise ValueError(FailureType.DataError, 'Safety check failed')


def check_gas(msg: EthereumSignTx) -> bool:
    if msg.gas_price is None or msg.gas_limit is None:
        return False
    if len(msg.gas_price) + len(msg.gas_limit) > 30:
        # sanity check that fee doesn't overflow
        return False
    return True


def check_to(msg: EthereumTxRequest) -> bool:
    if msg.to == b'':
        if msg.data_length == 0:
            # sending transaction to address 0 (contract creation) without a data field
            return False
    else:
        if len(msg.to) != 20:
            return False
    return True


def sanitize(msg):
    if msg.value is None:
        msg.value = b''
    if msg.data_initial_chunk is None:
        msg.data_initial_chunk = b''
    if msg.data_length is None:
        msg.data_length = 0
    if msg.to is None:
        msg.to = b''
    if msg.nonce is None:
        msg.nonce = b''
    if msg.chain_id is None:
        msg.chain_id = 0
    return msg
