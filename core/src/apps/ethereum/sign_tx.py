from micropython import const
from typing import TYPE_CHECKING
from ubinascii import unhexlify

from trezor import TR
from trezor.crypto import rlp
from trezor.messages import EthereumTxRequest
from trezor.utils import HashWriter
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
    from typing import Any, Coroutine, Iterable

    from trezor.messages import EthereumSignTx, EthereumTxAck
    from trezor.ui.layouts import StrPropertyType

    from apps.common.keychain import Keychain
    from apps.common.payment_request import PaymentRequestVerifier

    from .definitions import Definitions
    from .helpers import ConfirmDataFn
    from .keychain import MsgInSignTx


# Maximum chain_id which returns the full signature_v (which must fit into an uint32).
# chain_ids larger than this will only return one bit and the caller must recalculate
# the full value: v = 2 * chain_id + 35 + v_bit
_MAX_CHAIN_ID = const(0xFFFF_FFFF - 36) // 2

# EIP-7702

_EIP_7702_TX_TYPE = const(4)
EIP_7702_KNOWN_ADDRESSES = {
    unhexlify("000000009B1D0aF20D8C6d0A44e162d11F9b8f00"): "Uniswap",
    unhexlify("69007702764179f14F51cdce752f4f775d74E139"): "alchemyplatform",
    unhexlify("5A7FC11397E9a8AD41BF10bf13F22B0a63f96f6d"): "AmbireTech",
    unhexlify("63c0c19a282a1b52b07dd5a65b58948a07dae32b"): "MetaMask",
    unhexlify(
        "4Cd241E8d1510e30b2076397afc7508Ae59C66c9"
    ): "Ethereum Foundation AA team",
    unhexlify("17c11FDdADac2b341F2455aFe988fec4c3ba26e3"): "Luganodes",
}


@with_keychain_from_chain_id
async def sign_tx(
    msg: EthereumSignTx,
    keychain: Keychain,
    defs: Definitions,
) -> EthereumTxRequest:
    from trezor.crypto.hashlib import sha3_256
    from trezor.ui.layouts import show_continue_in_app
    from trezor.utils import HashWriter

    from apps.common import paths, safety_checks

    from .helpers import format_ethereum_amount, get_fee_items_regular

    # local_cache_attribute
    data_length = msg.data_length
    tx_type = msg.tx_type
    network = defs.network

    check_common_fields(msg)

    address_bytes = bytes_from_address(msg.to)

    valid_tx_types = (1, 6, _EIP_7702_TX_TYPE, None)
    if tx_type not in valid_tx_types:
        raise DataError("tx_type out of bounds")
    if tx_type == _EIP_7702_TX_TYPE:
        if safety_checks.is_strict():
            raise DataError("EIP-7702 not allowed in strict checks")
        if address_bytes not in EIP_7702_KNOWN_ADDRESSES:
            raise DataError("Unknown EIP-7702 address")
    if len(msg.gas_price) + len(msg.gas_limit) > 30:
        raise DataError("Fee overflow")

    # have the user confirm signing
    await paths.validate_path(keychain, msg.address_n)
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

    sha = HashWriter(sha3_256(keccak=True))
    rlp.write_header(sha, _get_digest_length(msg, data_length), rlp.LIST_HEADER_BYTE)

    if tx_type is not None:
        rlp.write(sha, tx_type)

    for field in (msg.nonce, msg.gas_price, msg.gas_limit, address_bytes, msg.value):
        rlp.write(sha, field)

    initial_data = await request_initial_data(msg, sha)

    confirm_data_chunk, confirm_summary = await confirm_tx_data(
        initial_data,
        msg,
        defs,
        tx_type,
        address_bytes,
        maximum_fee,
        fee_items,
        payment_req_verifier,
    )

    # `confirm_data_chunk` and `confirm_summary` can be `None`
    # if we clear signed so there is nothing more to confirm

    if confirm_data_chunk is not None:
        await confirm_data_chunk(initial_data)

        data_left = data_length - len(initial_data)
        while data_left > 0:
            resp = await send_request_chunk(data_left)
            chunk = resp.data_chunk
            await confirm_data_chunk(chunk)
            data_left -= len(chunk)
            sha.extend(chunk)

    if confirm_summary is not None:
        # blind signer's summary
        await confirm_summary

    # eip 155 replay protection
    rlp.write(sha, msg.chain_id)
    rlp.write(sha, 0)
    rlp.write(sha, 0)

    digest = sha.get_digest()

    # transaction data confirmed, proceed with signing
    result = _sign_digest(msg, keychain, digest)

    show_continue_in_app(TR.send__transaction_signed)
    return result


_MAX_DATA_STORED = const(4096)
_DATA_CHUNK_SIZE = const(1024)


async def request_initial_data(msg: MsgInSignTx, sha: HashWriter) -> AnyBytes:
    """Request at most `MAX_DATA_STORED` which we keep locally"""

    data_length = msg.data_length
    if data_length > len(msg.data_initial_chunk):
        # pre-allocate memory
        initial_data = bytearray(min(data_length, _MAX_DATA_STORED))

        chunk = msg.data_initial_chunk
        initial_data[0 : len(chunk)] = chunk
        initial_data_length = len(chunk)
        rlp.write_header(sha, data_length, rlp.STRING_HEADER_BYTE, chunk)
        sha.extend(chunk)
        data_left = data_length - initial_data_length
        while (
            data_left > 0 and initial_data_length + _DATA_CHUNK_SIZE <= _MAX_DATA_STORED
        ):
            resp = await send_request_chunk(data_left)
            chunk = resp.data_chunk
            initial_data[
                initial_data_length : initial_data_length + len(resp.data_chunk)
            ] = chunk
            data_left -= len(chunk)
            initial_data_length += len(chunk)
            sha.extend(chunk)
    else:
        initial_data = msg.data_initial_chunk
        initial_data_length = len(msg.data_initial_chunk)
        rlp.write_header(
            sha, data_length, rlp.STRING_HEADER_BYTE, msg.data_initial_chunk
        )
        sha.extend(msg.data_initial_chunk)

    return initial_data


async def confirm_tx_data(
    initial_data: AnyBytes,
    msg: MsgInSignTx,
    defs: Definitions,
    tx_type: int | None,
    address_bytes: bytes,
    maximum_fee: str,
    fee_items: Iterable[StrPropertyType],
    payment_request_verifier: PaymentRequestVerifier | None,
) -> tuple[ConfirmDataFn | None, Coroutine[Any, Any, None] | None]:
    """Returns data chunk callback and transaction summary layout to be awaited.
    [None, None] implies clear signing attempted and succeeded."""

    from trezor.ui.layouts import confirm_value

    from . import clear_signing, staking
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
        return staking_approver

    if tx_type == _EIP_7702_TX_TYPE:
        # we have already made sure that the address is a known address
        # as part of the initial validation
        await confirm_value(
            TR.ethereum__eip_7702_title,
            EIP_7702_KNOWN_ADDRESSES[address_bytes],
            TR.ethereum__eip_7702,
            "confirm_provider",
        )

    value = int.from_bytes(msg.value, "big")

    try:
        clear_signed = await clear_signing.try_parse(
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
        assert data_length == 0

        # If a payment_request_verifier is provided, then msg.payment_req must have been set.
        assert msg.payment_req is not None
        assert recipient_str is not None

        payment_request_verifier.add_output(value, recipient_str or "")
        payment_request_verifier.verify()
        return get_progress_indicator(data_length), require_confirm_payment_request(
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

        return confirm_data_chunk, require_confirm_tx(
            recipient_str,
            format_ethereum_amount(value, token, network),
            address_bytes,
            msg.address_n,
            maximum_fee,
            fee_items,
            token,
            is_send=(data_length == 0 and tx_type != _EIP_7702_TX_TYPE),
            chunkify=bool(msg.chunkify),
        )
    else:
        return None, None


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


async def send_request_chunk(data_left: int) -> EthereumTxAck:
    from trezor.messages import EthereumTxAck
    from trezor.wire.context import call

    req = EthereumTxRequest()
    req.data_length = min(data_left, _DATA_CHUNK_SIZE)
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
