from typing import TYPE_CHECKING

from trezor.crypto import rlp
from trezor.messages import EthereumNetworkInfo, EthereumTxRequest
from trezor.wire import DataError

from .helpers import address_from_bytes, bytes_from_address
from .keychain import with_keychain_from_chain_id

if TYPE_CHECKING:
    from typing import Any

    from apps.common.keychain import Keychain
    from trezor.messages import EthereumSignTx, EthereumTxAck, EthereumTokenInfo
    from trezor.ui.layouts.common import PropertyType

    from .definitions import Definitions
    from .keychain import MsgInSignTx


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
    from trezor.utils import HashWriter
    from trezor.crypto.hashlib import sha3_256
    from .layout import require_confirm_fee

    # check
    if msg.tx_type not in [1, 6, None]:
        raise DataError("tx_type out of bounds")
    if len(msg.gas_price) + len(msg.gas_limit) > 30:
        raise DataError("Fee overflow")

    token, address_bytes, _recipient, value = await sign_tx_inner(msg, keychain, defs)

    data_total = msg.data_length

    await require_confirm_fee(
        value,
        int.from_bytes(msg.gas_price, "big"),
        int.from_bytes(msg.gas_limit, "big"),
        defs.network,
        token,
    )

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


async def sign_tx_inner(
    msg: MsgInSignTx,
    keychain: Keychain,
    defs: Definitions,
) -> tuple[EthereumTokenInfo | None, bytes, bytes, int | None]:
    from . import tokens
    from .layout import (
        require_confirm_data,
        require_confirm_tx,
        require_confirm_unknown_token,
    )
    from trezor.ui.layouts import confirm_properties
    from trezor.enums import ButtonRequestType
    from apps.common import paths
    from ubinascii import hexlify

    check_common_fields(msg)
    await paths.validate_path(keychain, msg.address_n)

    data_initial_chunk = memoryview(msg.data_initial_chunk)  # local_cache_attribute
    token = None
    address_bytes = recipient = bytes_from_address(msg.to)
    value = int.from_bytes(msg.value, "big")

    FUNCTION_HASH_LENGTH = (
        4  # ETH function hashes are truncated to 4 bytes in calldata for some reason.
    )
    if (
        len(msg.to) in (40, 42)
        and len(msg.value) == 0
        and msg.data_length >= FUNCTION_HASH_LENGTH
        and len(data_initial_chunk) >= FUNCTION_HASH_LENGTH
    ):
        function_hash = int.from_bytes(data_initial_chunk[:FUNCTION_HASH_LENGTH], "big")

        if value:
            raise DataError(
                "Expecting zero or None as native transaction value when calling smart contract functions"
            )
        # Force 0 value to None to signify that we are not spending regular ethereum in later dialogs
        value = None

        confirm_props: list[PropertyType] = []

        # Bother the user with confirming unknown tokens if we are indeed calling a function and not just transferring value.
        token = defs.get_token(address_bytes)
        if token is tokens.UNKNOWN_TOKEN:
            await require_confirm_unknown_token(address_bytes, defs.network)
        else:
            confirm_props.append(("Token:", token.name))

        if defs.network:
            confirm_props.append(("Network:", defs.network.name))

        if abi := _fetch_function_abi(function_hash):
            confirm_props.extend(
                _fetch_abi_input_properties(
                    abi["inputs"],
                    data_initial_chunk[FUNCTION_HASH_LENGTH:],
                    defs.network,
                )
            )

            await confirm_properties(
                "confirm_call",
                abi["description"],
                confirm_props,
                hold=True,
                br_code=ButtonRequestType.SignTx,
            )
        elif token:
            confirm_props.append(
                ("Raw calldata:", f"0x{hexlify(data_initial_chunk).decode()}")
            )

            await confirm_properties(
                "confirm_unknown_abi",
                "Confirm calling function",
                confirm_props,
                hold=True,
                br_code=ButtonRequestType.SignTx,
            )

    if value is not None:
        await require_confirm_tx(recipient, value, defs.network, token)

    if token is None and msg.data_length > 0:
        await require_confirm_data(msg.data_initial_chunk, msg.data_length)

    return token, address_bytes, recipient, value


def _fetch_function_abi(function_hash: int) -> dict[str, Any] | None:
    # Current limitations:
    # * Only contains ERC-20 functions
    # * Does not include outputs, not shown in UI
    # In the future this lookup could be provided by the host, signed with SL keys.
    ABI_DB: dict[int, dict[str, Any]] = {
        0xDD62ED3E: {
            "name": "allowance",
            "description": "ERC 20 Fetch allowance amount",
            "inputs": [
                {"name": "owner", "type": "address"},
                {"name": "spender", "type": "address"},
            ],
        },
        0x095EA7B3: {
            "name": "approve",
            "description": "ERC 20 Approve allowance",
            "inputs": [
                {
                    "name": "spender",
                    "type": "address",
                },
                {
                    "name": "value",
                    "type": "uint256",
                },
            ],
        },
        0xA9059CBB: {
            "name": "transfer",
            "description": "ERC 20 Transfer",
            "inputs": [
                {
                    "name": "to",
                    "type": "address",
                },
                {
                    "name": "value",
                    "type": "uint256",
                },
            ],
        },
        0x23B872DD: {
            "name": "transferFrom",
            "description": "ERC 20 Transfer from",
            "inputs": [
                {
                    "name": "from",
                    "type": "address",
                },
                {
                    "name": "to",
                    "type": "address",
                },
                {
                    "name": "value",
                    "type": "uint256",
                },
            ],
        },
    }
    return ABI_DB.get(function_hash)


def _fetch_abi_input_properties(
    input_defs: list[dict[str, str]], calldata: memoryview, network: EthereumNetworkInfo
) -> list[PropertyType]:
    expected_data_length = len(input_defs) * 32
    if len(calldata) != expected_data_length:
        raise DataError(
            f"Function definition requires more parameter data than provided in calldata ({len(calldata)} vs {expected_data_length})."
        )

    input_props: list[PropertyType] = []

    for index, input_def in enumerate(input_defs):
        input_type = input_def["type"]
        input_name = input_def["name"]

        if input_type == "address":
            # We skip over the first 12 bytes of zero padding in the address
            input_address = calldata[12 + (index * 32) : 32 + (index * 32)]
            input_props.append(
                (
                    f"{input_name} ({input_type}):",
                    address_from_bytes(input_address, network),
                )
            )
        elif input_type == "uint256":
            input_uint = int.from_bytes(
                calldata[(index * 32) : 32 + (index * 32)], "big"
            )
            input_props.append((f"{input_name} ({input_type}):", str(input_uint)))
        else:
            raise DataError(
                "Currently unsupported type returned by _fetch_function_abi: "
                + input_type
            )

    return input_props


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
