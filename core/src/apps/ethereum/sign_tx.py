from typing import TYPE_CHECKING

from trezor import utils
from trezor.crypto import rlp
from trezor.messages import EthereumTxRequest
from trezor.utils import BufferReader
from trezor.wire import DataError

from apps.ethereum import staking_tx_constants as constants

from .helpers import bytes_from_address
from .keychain import with_keychain_from_chain_id

if TYPE_CHECKING:
    from typing import Iterable

    from trezor.messages import (
        EthereumNetworkInfo,
        EthereumSignTx,
        EthereumTokenInfo,
        EthereumTxAck,
    )
    from trezor.ui.layouts.common import ProgressLayout

    from apps.common.keychain import Keychain

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
    from trezor.crypto.hashlib import sha3_256
    from trezor.utils import HashWriter

    from apps.common import paths

    from .helpers import format_ethereum_amount, get_fee_items_regular

    data_total = msg.data_length  # local_cache_attribute

    # check
    if msg.tx_type not in [1, 6, None]:
        raise DataError("tx_type out of bounds")
    if len(msg.gas_price) + len(msg.gas_limit) > 30:
        raise DataError("Fee overflow")
    check_common_fields(msg)

    # have a user confirm signing
    await paths.validate_path(keychain, msg.address_n)
    address_bytes = bytes_from_address(msg.to)
    gas_price = int.from_bytes(msg.gas_price, "big")
    gas_limit = int.from_bytes(msg.gas_limit, "big")
    maximum_fee = format_ethereum_amount(gas_price * gas_limit, None, defs.network)
    fee_items = get_fee_items_regular(
        gas_price,
        gas_limit,
        defs.network,
    )
    await confirm_tx_data(msg, defs, address_bytes, maximum_fee, fee_items, data_total)

    _start_progress()

    _render_progress(30)

    # sign
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

    _render_progress(60)

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

    _finish_progress()

    return result


async def confirm_tx_data(
    msg: MsgInSignTx,
    defs: Definitions,
    address_bytes: bytes,
    maximum_fee: str,
    fee_items: Iterable[tuple[str, str]],
    data_total_len: int,
) -> None:
    # function distinguishes between staking / smart contracts / regular transactions
    from .layout import require_confirm_other_data, require_confirm_tx

    if await handle_staking(msg, defs.network, address_bytes, maximum_fee, fee_items):
        return

    # Handle ERC-20, currently only 'transfer' function
    token, recipient, value = await handle_erc20_transfer(msg, defs, address_bytes)

    if token is None and data_total_len > 0:
        await require_confirm_other_data(msg.data_initial_chunk, data_total_len)

    await require_confirm_tx(
        recipient,
        value,
        maximum_fee,
        fee_items,
        defs.network,
        token,
        bool(msg.chunkify),
    )


async def handle_staking(
    msg: MsgInSignTx,
    network: EthereumNetworkInfo,
    address_bytes: bytes,
    maximum_fee: str,
    fee_items: Iterable[tuple[str, str]],
) -> bool:

    data_reader = BufferReader(msg.data_initial_chunk)
    if data_reader.remaining_count() < constants.SC_FUNC_SIG_BYTES:
        return False

    func_sig = data_reader.read_memoryview(constants.SC_FUNC_SIG_BYTES)
    if address_bytes in constants.ADDRESSES_POOL:
        if func_sig == constants.SC_FUNC_SIG_STAKE:
            await _handle_staking_tx_stake(
                data_reader, msg, network, address_bytes, maximum_fee, fee_items
            )
            return True
        if func_sig == constants.SC_FUNC_SIG_UNSTAKE:
            await _handle_staking_tx_unstake(
                data_reader, msg, network, address_bytes, maximum_fee, fee_items
            )
            return True

    if address_bytes in constants.ADDRESSES_ACCOUNTING:
        if func_sig == constants.SC_FUNC_SIG_CLAIM:
            await _handle_staking_tx_claim(
                data_reader,
                address_bytes,
                maximum_fee,
                fee_items,
                network,
                bool(msg.chunkify),
            )
            return True

    # data not corresponding to staking transaction
    return False


async def handle_erc20_transfer(
    msg: MsgInSignTx,
    definitions: Definitions,
    address_bytes: bytes,
) -> tuple[EthereumTokenInfo | None, bytes, int]:
    from . import tokens
    from .layout import require_confirm_unknown_token

    data_initial_chunk = msg.data_initial_chunk  # local_cache_attribute
    token = None
    recipient = address_bytes
    value = int.from_bytes(msg.value, "big")
    if (
        len(msg.to) in (40, 42)
        and len(msg.value) == 0
        and msg.data_length == 68
        and len(data_initial_chunk) == 68
        and data_initial_chunk[:16]
        == b"\xa9\x05\x9c\xbb\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    ):
        token = definitions.get_token(address_bytes)
        recipient = data_initial_chunk[16:36]
        value = int.from_bytes(data_initial_chunk[36:68], "big")

        if token is tokens.UNKNOWN_TOKEN:
            await require_confirm_unknown_token(address_bytes)

    return token, recipient, value


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


async def _handle_staking_tx_stake(
    data_reader: BufferReader,
    msg: MsgInSignTx,
    network: EthereumNetworkInfo,
    address_bytes: bytes,
    maximum_fee: str,
    fee_items: Iterable[tuple[str, str]],
) -> None:
    from .layout import require_confirm_stake

    # stake args:
    # - arg0: uint64, source (should be 1)
    try:
        source = int.from_bytes(
            data_reader.read_memoryview(constants.SC_ARGUMENT_BYTES), "big"
        )
        if source != 1:
            raise ValueError  # wrong value of 1st argument ('source' should be 1)
        if data_reader.remaining_count() != 0:
            raise ValueError  # wrong number of arguments for stake (should be 1)
    except (ValueError, EOFError):
        raise DataError("Invalid staking transaction call")

    await require_confirm_stake(
        address_bytes,
        int.from_bytes(msg.value, "big"),
        maximum_fee,
        fee_items,
        network,
        bool(msg.chunkify),
    )


async def _handle_staking_tx_unstake(
    data_reader: BufferReader,
    msg: MsgInSignTx,
    network: EthereumNetworkInfo,
    address_bytes: bytes,
    maximum_fee: str,
    fee_items: Iterable[tuple[str, str]],
) -> None:
    from .layout import require_confirm_unstake

    # unstake args:
    # - arg0: uint256, value
    # - arg1:  uint16, isAllowedInterchange (bool)
    # - arg2: uint64, source, should be 1
    try:
        value = int.from_bytes(
            data_reader.read_memoryview(constants.SC_ARGUMENT_BYTES), "big"
        )
        _ = data_reader.read_memoryview(constants.SC_ARGUMENT_BYTES)  # skip arg1
        source = int.from_bytes(
            data_reader.read_memoryview(constants.SC_ARGUMENT_BYTES), "big"
        )
        if source != 1:
            raise ValueError  # wrong value of 3rd argument ('source' should be 1)
        if data_reader.remaining_count() != 0:
            raise ValueError  # wrong number of arguments for unstake (should be 3)
    except (ValueError, EOFError):
        raise DataError("Invalid staking transaction call")

    await require_confirm_unstake(
        address_bytes,
        value,
        maximum_fee,
        fee_items,
        network,
        bool(msg.chunkify),
    )


async def _handle_staking_tx_claim(
    data_reader: BufferReader,
    staking_addr: bytes,
    maximum_fee: str,
    fee_items: Iterable[tuple[str, str]],
    network: EthereumNetworkInfo,
    chunkify: bool,
) -> None:
    from .layout import require_confirm_claim

    # claim has no args
    if data_reader.remaining_count() != 0:
        raise DataError("Invalid staking transaction call")

    await require_confirm_claim(staking_addr, maximum_fee, fee_items, network, chunkify)


_progress_obj: ProgressLayout | None = None


def _start_progress() -> None:
    from trezor import TR, workflow
    from trezor.ui.layouts.progress import progress

    global _progress_obj

    if not utils.DISABLE_ANIMATION:
        # Because we are drawing to the screen manually, without a layout, we
        # should make sure that no other layout is running.
        workflow.close_others()
        _progress_obj = progress(title=TR.progress__signing_transaction)


def _render_progress(progress: int) -> None:
    global _progress_obj
    if _progress_obj is not None:
        _progress_obj.report(progress)


def _finish_progress() -> None:
    global _progress_obj
    _progress_obj = None
