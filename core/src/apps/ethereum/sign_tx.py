from typing import TYPE_CHECKING

from trezor.crypto import rlp
from trezor.messages import EthereumTxRequest
from trezor.wire import DataError

from .helpers import bytes_from_address
from .keychain import with_keychain_from_chain_id

if TYPE_CHECKING:
    from trezor.messages import EthereumSignTx, EthereumTokenInfo, EthereumTxAck

    from apps.common.keychain import Keychain

    from .definitions import Definitions
    from .keychain import MsgInSignTx
    from typing import Any


# Maximum chain_id which returns the full signature_v (which must fit into an uint32).
# chain_ids larger than this will only return one bit and the caller must recalculate
# the full value: v = 2 * chain_id + 35 + v_bit
MAX_CHAIN_ID = (0xFFFF_FFFF - 36) // 2


@with_keychain_from_chain_id
async def sign_tx(
    msg: EthereumSignTx,
    keychain: Keychain,
    defs: Definitions,
) -> EthereumTxRequest:
    from trezor.crypto.hashlib import sha3_256
    from trezor.utils import HashWriter

    from apps.common import paths
    from .layout import require_confirm_data, require_confirm_tx

    # check
    if msg.tx_type not in [1, 6, None]:
        raise DataError("tx_type out of bounds")
    if len(msg.gas_price) + len(msg.gas_limit) > 30:
        raise DataError("Fee overflow")
    check_common_fields(msg)

    await paths.validate_path(keychain, msg.address_n)

    address_bytes = bytes_from_address(msg.to)
    token, value = await sign_tx_common(msg, defs, address_bytes)

    await require_confirm_tx(
        address_bytes,
        value,
        int.from_bytes(msg.gas_price, "big"),
        int.from_bytes(msg.gas_limit, "big"),
        defs.network,
        token,
        bool(msg.chunkify),
    )

    data_total = msg.data_length
    data = bytearray()
    data += msg.data_initial_chunk
    data_left = data_total - len(msg.data_initial_chunk)

    total_length = _get_total_length(msg, data_total)

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
        resp = await send_request_chunk(data_left)
        data_left -= len(resp.data_chunk)
        sha.extend(resp.data_chunk)

    # eip 155 replay protection
    rlp.write(sha, msg.chain_id)
    rlp.write(sha, 0)
    rlp.write(sha, 0)

    digest = sha.get_digest()
    result = _sign_digest(msg, keychain, digest)

    return result


async def sign_tx_common(
    msg: MsgInSignTx,
    definitions: Definitions,
    address_bytes: bytes,
) -> tuple[EthereumTokenInfo | None, int]:
    from .layout import (
        require_confirm_unknown_token,
        require_confirm_smart_contract,
        require_confirm_tx,
        require_confirm_data,
    )
    from . import tokens

    data_initial_chunk = msg.data_initial_chunk  # local_cache_attribute
    token = None
    value = int.from_bytes(msg.value, "big")
    if len(msg.to) in (40, 42) and value == 0:
        # Smart Contract
        func_name, func_args, transfer = _resolve_tx_data_field(data_initial_chunk)
        # TODO handle ValueError from _resolve_tx_data_field, presently it fails `test_data_streaming`
        token = definitions.get_token(address_bytes)
        if token is tokens.UNKNOWN_TOKEN:
            await require_confirm_unknown_token(address_bytes)
        if transfer[0]:
            # 'transfer' functions should override the value
            arg_val_idx = transfer[1]
            value = int(func_args[arg_val_idx][1])
        else:
            # we want to show default network at summary screen (i.e. 0 ETH)
            token = None
        await require_confirm_smart_contract(func_name, func_args)
    else:
        # Regular transaction
        await require_confirm_tx(address_bytes, value, definitions.network, token)
        if msg.data_length > 0:
            await require_confirm_data(data_initial_chunk, msg.data_length)

    return token, value


def _resolve_type(val: memoryview, type_str: str) -> str:
    from ubinascii import hexlify
    from .helpers import address_from_bytes

    if type_str == "int":
        return str(int.from_bytes(val, "big"))
    elif type_str == "str":
        # TODO improve shown text
        return bytes(val).decode()
    elif type_str == "bytes":
        return hexlify(val).decode()
    elif type_str == "address":
        return address_from_bytes(val[-20:])
    else:
        raise ValueError


FUNCTIONS_DEF: dict[bytes, dict[str, Any]] = {
    b"\xa9\x05\x9c\xbb": {
        "name": "transfer",
        "args": [
            ("Recipient", "address"),
            ("Amount", "int"),
        ],
        "transfer": (True, 1),
    },
    b"\x09\x5e\xa7\xb3": {
        "name": "approve",
        "args": [
            ("Address", "address"),
            ("Amount", "int"),
        ],
        "transfer": (False, 0),
    },
    b"\x00\x00\x00\x42": {
        "name": "args_test",
        "args": [
            ("Arg0_int", "int"),
            ("Arg1_str", "str"),
            ("Arg2_bytes", "bytes"),
            ("Arg3_address", "address"),
        ],
        "transfer": (False, 0),
        # TODO token to address assignment is done by additional entry, where:
        #   - 1st value is the idx of the value of a token
        #   - 2nd value is the idx of the address of the token -> to be used in the `definitions.get_token(addr)` call
        #   - if 1st == 2nd: token is assigned based on contract address
        # "token_assign": (0, 3),
    },
}


def _resolve_tx_data_field(
    data_bytes: bytes,
) -> tuple[str, list[tuple[str, str | bytes]], tuple[bool, int]]:
    from ubinascii import hexlify

    data_args_len = len(data_bytes)
    N_BYTES_FUNC = 4
    N_BYTES_ARG = 32
    n_args = (data_args_len - N_BYTES_FUNC) // N_BYTES_ARG
    data = memoryview(data_bytes)

    def _data_field_aligned(data_args_len: int, n_args: int) -> bool:
        # checks if "Data" field doesn't have trailing bytes
        return data_args_len == (n_args * N_BYTES_ARG + N_BYTES_FUNC)

    def _get_nth_arg(data_mv: memoryview, n: int) -> memoryview:
        # returns slice of the nth argument in "Data" field
        beg = (n + 0) * N_BYTES_ARG + N_BYTES_FUNC
        end = (n + 1) * N_BYTES_ARG + N_BYTES_FUNC
        return data_mv[beg:end]

    if data_args_len < N_BYTES_FUNC or not _data_field_aligned(data_args_len, n_args):
        raise ValueError

    func_signature_bytes = data_bytes[:N_BYTES_FUNC]
    func_def = FUNCTIONS_DEF.get(func_signature_bytes, None)
    if func_def is not None and n_args == len(func_def["args"]):
        func_name = func_def["name"]
        func_args = [
            (f"{name}:", _resolve_type(_get_nth_arg(data, i), type_str))
            for i, (name, type_str) in enumerate(func_def["args"])
        ]
        transfer = func_def["transfer"]
    else:
        func_name = hexlify(func_signature_bytes).decode()
        func_args = [(f"Input {i}:", _get_nth_arg(data, i)) for i in range(n_args)]
        transfer = (False, 0)
    return (func_name, func_args, transfer)


def _get_total_length(msg: EthereumSignTx, data_total: int) -> int:
    length = 0
    if msg.tx_type is not None:
        length += rlp.length(msg.tx_type)

    fields: tuple[rlp.RLPItem, ...] = (
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


async def send_request_chunk(data_left: int) -> EthereumTxAck:
    from trezor.messages import EthereumTxAck
    from trezor.wire.context import call

    # TODO: layoutProgress ?
    req = EthereumTxRequest()
    req.data_length = min(data_left, 1024)
    return await call(req, EthereumTxAck)


def _sign_digest(
    msg: EthereumSignTx, keychain: Keychain, digest: bytes
) -> EthereumTxRequest:
    from trezor.crypto.curve import secp256k1

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


def check_common_fields(msg: MsgInSignTx) -> None:
    data_length = msg.data_length  # local_cache_attribute

    if data_length > 0:
        if not msg.data_initial_chunk:
            raise DataError("Data length provided, but no initial chunk")
        # Our encoding only supports transactions up to 2^24 bytes. To
        # prevent exceeding the limit we use a stricter limit on data length.
        if data_length > 16_000_000:
            raise DataError("Data length exceeds limit")
        if len(msg.data_initial_chunk) > data_length:
            raise DataError("Invalid size of initial chunk")

    if len(msg.to) not in (0, 40, 42):
        raise DataError("Invalid recipient address")

    if not msg.to and data_length == 0:
        # sending transaction to address 0 (contract creation) without a data field
        raise DataError("Contract creation without data")

    if msg.chain_id == 0:
        raise DataError("Chain ID out of bounds")
