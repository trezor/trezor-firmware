from micropython import const
from typing import TYPE_CHECKING

from trezor import TR
from trezor.crypto import rlp
from trezor.messages import EthereumTxRequest
from trezor.wire import DataError

from .helpers import (
    address_from_bytes,
    bytes_from_address,
    get_data_confirmer,
    get_progress_indicator,
)
from .keychain import with_keychain_from_chain_id

if TYPE_CHECKING:
    from buffer_types import AnyBytes
    from typing import Sequence

    from trezor.messages import EthereumSignTx
    from trezor.ui.layouts import StrPropertyType
    from trezor.utils import HashWriter

    from apps.common.keychain import Keychain
    from apps.common.payment_request import PaymentRequestVerifier

    from .definitions import Definitions
    from .helpers import ConfirmDataFn, DataChunkLoader
    from .keychain import MsgInSignTx


# Maximum chain_id which returns the full signature_v (which must fit into an uint32).
# chain_ids larger than this will only return one bit and the caller must recalculate
# the full value: v = 2 * chain_id + 35 + v_bit
_MAX_CHAIN_ID = const(0xFFFF_FFFF - 36) // 2


@with_keychain_from_chain_id
async def sign_tx(
    msg: EthereumSignTx,
    keychain: Keychain,
    defs: Definitions,
) -> EthereumTxRequest:
    from trezor.ui.layouts import show_continue_in_app

    from apps.common import paths

    from .helpers import format_ethereum_amount, get_fee_items_regular, keccak256

    # local_cache_attribute
    data_length = msg.data_length
    tx_type = msg.tx_type
    network = defs.network

    check_common_fields(msg)

    address_bytes = bytes_from_address(msg.to)

    valid_tx_types = (1, 6, None)
    if tx_type not in valid_tx_types:
        raise DataError("tx_type out of bounds")
    if len(msg.gas_price) + len(msg.gas_limit) > 30:
        raise DataError("Fee overflow")

    # have the user confirm signing
    await paths.validate_path(keychain, msg.address_n)
    sender_bytes = keychain.derive(msg.address_n).ethereum_pubkeyhash()
    gas_price = int.from_bytes(msg.gas_price, "big")
    gas_limit = int.from_bytes(msg.gas_limit, "big")
    maximum_fee = format_ethereum_amount(gas_price * gas_limit, None, network)
    fee_items = get_fee_items_regular(
        gas_price,
        gas_limit,
        network,
    )

    payment_req_verifier = None
    if msg.payment_req:
        from apps.common.payment_request import PaymentRequestVerifier

        slip44_id = paths.unharden(msg.address_n[1])
        payment_req_verifier = PaymentRequestVerifier(
            msg.payment_req,
            slip44_id,
            keychain,
            amount_size_bytes=32,
        )

    sha = keccak256()
    rlp.write_header(sha, _get_digest_length(msg, data_length), rlp.LIST_HEADER_BYTE)

    if tx_type is not None:
        rlp.write(sha, tx_type)

    for field in (msg.nonce, msg.gas_price, msg.gas_limit, address_bytes, msg.value):
        rlp.write(sha, field)

    initial_data = await request_initial_data(msg, sha)

    # Confirm the transaction, using special layouts for staking, yielding and clear-signing (if supported).
    await confirm_tx_data(
        initial_data,
        msg,
        defs,
        address_bytes,
        maximum_fee,
        fee_items,
        payment_req_verifier,
        sender_bytes,
        # Hash and confirm the rest of transaction calldata while loading it from the host.
        create_data_chunk_loader(sha),
    )

    # eip 155 replay protection
    rlp.write(sha, msg.chain_id)
    rlp.write(sha, 0)
    rlp.write(sha, 0)

    digest = sha.get_digest()

    # transaction data confirmed, proceed with signing
    result = _sign_digest(msg, keychain, digest)

    show_continue_in_app(TR.send__transaction_signed)
    return result


_MAX_DATA_STORED = const(6144)
_DATA_CHUNK_SIZE = const(1024)


async def request_initial_data(msg: MsgInSignTx, sha: HashWriter) -> AnyBytes:
    """Request at most `MAX_DATA_STORED` which we keep locally"""
    from trezor.utils import empty_bytearray

    data_length = msg.data_length
    if data_length > len(msg.data_initial_chunk):
        # pre-allocate memory
        buf_capacity = min(data_length, _MAX_DATA_STORED)
        buf = empty_bytearray(buf_capacity)
        buf.extend(msg.data_initial_chunk)

        # preload `buf_capacity` bytes from the host into `buf`
        while (data_left := buf_capacity - len(buf)) > 0:
            chunk = await _get_next_chunk(data_left)
            buf.extend(chunk)
    else:
        buf = msg.data_initial_chunk

    rlp.write_header(sha, data_length, rlp.STRING_HEADER_BYTE, buf)
    sha.extend(buf)
    return buf


async def confirm_tx_data(
    initial_data: AnyBytes,
    msg: MsgInSignTx,
    defs: Definitions,
    address_bytes: bytes,
    maximum_fee: str,
    fee_items: Sequence[StrPropertyType],
    payment_request_verifier: PaymentRequestVerifier | None,
    sender_bytes: AnyBytes,
    data_chunk_loader: DataChunkLoader,
) -> None:
    """Clear-sign the transaction or confirm calldata chunks."""

    from . import clear_signing, staking, yielding
    from .helpers import format_ethereum_amount
    from .layout import require_confirm_payment_request, require_confirm_tx

    # local_cache_attribute
    data_length = msg.data_length
    network = defs.network

    staking_approver = staking.get_approver(
        msg, network, address_bytes, maximum_fee, fee_items
    )
    if staking_approver is not None:
        if payment_request_verifier is not None:
            raise DataError("Payment Requests don't support staking")
        return await staking_approver

    yielding_approver = await yielding.get_approver(
        msg, initial_data, network, address_bytes, maximum_fee, fee_items, sender_bytes
    )
    if yielding_approver is not None:
        if payment_request_verifier is not None:
            raise DataError("Payment Requests don't support yielding")
        return await yielding_approver

    value = int.from_bytes(msg.value, "big")

    if len(initial_data) < data_length:
        # Don't even attempt to clear sign if we have a calldata larger than `MAX_DATA_STORED`.
        # this is because clear signing doesn't currently support fetching additional data,
        # which is because if it did, we would not be able to fall back to blind signing anymore.
        clear_signed = False
    else:
        try:
            clear_signed = await clear_signing.try_confirm(
                initial_data,
                address_bytes,
                msg,
                defs,
                maximum_fee,
                fee_items,
                payment_request_verifier,
            )
        except clear_signing.ClearSigningFailed:
            clear_signed = False

    recipient_str = (
        address_from_bytes(address_bytes, network) if address_bytes else None
    )

    if payment_request_verifier is not None:
        if data_length != 0:
            raise DataError(
                "Data length must be 0 when `payment_request_verifier` is provided."
            )

        if msg.payment_req is None:
            raise DataError(
                "Payment request (`payment_req`) must not be None when `payment_request_verifier` is provided."
            )

        assert recipient_str is not None

        payment_request_verifier.add_output(value, recipient_str or "")
        payment_request_verifier.verify()
        return await require_confirm_payment_request(
            recipient_str,
            msg.payment_req,
            msg.address_n,
            maximum_fee,
            fee_items,
            msg.chain_id,
            network,
            None,
            None,
        )
    elif not clear_signed:
        if data_length > 0:
            confirm_data_chunk = get_data_confirmer(data_length)
        else:
            confirm_data_chunk = get_progress_indicator(data_length)
        token = (
            None  # what we want to confirm here is the ETH amount being sent on-chain
        )

        # Stream, confirm and hash the rest of the calldata chunks.
        await _confirm_data_chunks(
            confirm_data_chunk, initial_data, data_length, data_chunk_loader
        )
        return await require_confirm_tx(
            recipient_str,
            format_ethereum_amount(value, token, network),
            address_bytes,
            msg.address_n,
            maximum_fee,
            fee_items,
            token,
            is_send=(data_length == 0),
            chunkify=bool(msg.chunkify),
        )


def _get_digest_length(msg: EthereumSignTx, data_total: int) -> int:
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


def create_data_chunk_loader(h: HashWriter) -> DataChunkLoader:
    async def data_chunk_loader(data_left: int) -> AnyBytes:
        chunk = await _get_next_chunk(data_left)
        h.extend(chunk)
        return chunk

    return data_chunk_loader


async def _confirm_data_chunks(
    confirm_data_chunk: ConfirmDataFn,
    initial_data: AnyBytes,
    data_length: int,
    data_chunk_loader: DataChunkLoader,
) -> None:
    await confirm_data_chunk(initial_data)
    data_left = data_length - len(initial_data)
    while data_left > 0:
        chunk = await data_chunk_loader(data_left)
        # `confirm_data_chunk` will raise on cancellation, so
        # `data_chunk_loader`-computed hash will be discarded.
        await confirm_data_chunk(chunk)
        data_left -= len(chunk)


async def _get_next_chunk(data_left: int) -> AnyBytes:
    from trezor.messages import EthereumTxAck
    from trezor.wire.context import call

    req = EthereumTxRequest()
    req.data_length = min(data_left, _DATA_CHUNK_SIZE)
    resp = await call(req, EthereumTxAck)
    data_chunk = resp.data_chunk
    if len(data_chunk) != req.data_length:
        raise DataError("Data length mismatch")
    return data_chunk


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
    if msg.chain_id > _MAX_CHAIN_ID:
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
