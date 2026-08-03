from micropython import const
from typing import TYPE_CHECKING

from trezor.crypto import rlp

from .helpers import bytes_from_address
from .keychain import with_keychain_from_chain_id

if TYPE_CHECKING:
    from trezor.messages import (
        EthereumAccessList,
        EthereumSignTxEIP1559,
        EthereumTxRequest,
    )
    from trezor.utils import HashWriter

    from apps.common.keychain import Keychain

    from .definitions import Definitions


_TX_TYPE = const(2)


def access_list_item(item: EthereumAccessList) -> rlp.RLPItem:
    return [bytes_from_address(item.address), item.storage_keys]


@with_keychain_from_chain_id
async def sign_tx_eip1559(
    msg: EthereumSignTxEIP1559,
    keychain: Keychain,
    defs: Definitions,
) -> EthereumTxRequest:
    from trezor import TR, wire
    from trezor.ui.layouts import show_continue_in_app

    from apps.common import paths

    from .helpers import format_ethereum_amount, get_fee_items_eip1559
    from .sign_tx import (
        check_common_fields,
        confirm_tx_data,
        create_data_chunk_loader,
        request_initial_data,
    )

    gas_limit = msg.gas_limit  # local_cache_attribute

    # check
    if len(msg.max_gas_fee) + len(gas_limit) > 30:
        raise wire.DataError("Fee overflow")
    if len(msg.max_priority_fee) + len(gas_limit) > 30:
        raise wire.DataError("Fee overflow")
    check_common_fields(msg)

    # have a user confirm signing
    await paths.validate_path(keychain, msg.address_n)
    sender_bytes = keychain.derive(msg.address_n).ethereum_pubkeyhash()
    address_bytes = bytes_from_address(msg.to)

    max_gas_fee = int.from_bytes(msg.max_gas_fee, "big")
    max_priority_fee = int.from_bytes(msg.max_priority_fee, "big")
    gas_limit = int.from_bytes(msg.gas_limit, "big")
    maximum_fee = format_ethereum_amount(max_gas_fee * gas_limit, None, defs.network)
    fee_items = get_fee_items_eip1559(
        max_gas_fee,
        max_priority_fee,
        gas_limit,
        defs.network,
    )

    payment_req_verifier = None
    if msg.payment_req:
        from apps.common.payment_request import PaymentRequestVerifier

        slip44_id = paths.unharden(msg.address_n[1])
        payment_req_verifier = PaymentRequestVerifier(
            msg.payment_req, slip44_id, keychain, amount_size_bytes=32
        )

    sha = _start_digest(msg)
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

    digest = _finish_digest(msg, sha)

    # transaction data confirmed, proceed with signing
    result = _sign_digest(msg, keychain, digest)

    show_continue_in_app(TR.send__transaction_signed)
    return result


def _start_digest(msg: EthereumSignTxEIP1559) -> HashWriter:
    from .helpers import keccak256

    fields: tuple[rlp.RLPItem, ...] = (
        msg.chain_id,
        msg.nonce,
        msg.max_priority_fee,
        msg.max_gas_fee,
        msg.gas_limit,
        bytes_from_address(msg.to),
        msg.value,
    )

    # fields length
    length = sum(rlp.length(field) for field in fields)

    # calldata length
    length += rlp.header_length(msg.data_length, msg.data_initial_chunk)
    length += msg.data_length

    # access_list length (streaming instead of full materialization)
    payload_length = sum(rlp.length(access_list_item(i)) for i in msg.access_list)
    access_list_length = rlp.header_length(payload_length) + payload_length
    length += access_list_length

    # hash only `_TX_TYPE`, RLP header and `fields` (see above).
    # calldata and access_list will be hashed later.
    sha = keccak256()

    rlp.write(sha, _TX_TYPE)
    rlp.write_header(sha, length, rlp.LIST_HEADER_BYTE)
    for field in fields:
        rlp.write(sha, field)
    return sha


def _finish_digest(msg: EthereumSignTxEIP1559, sha: HashWriter) -> bytes:
    # write_access list (streaming instead of full materialization)
    payload_length = sum(rlp.length(access_list_item(i)) for i in msg.access_list)
    rlp.write_header(sha, payload_length, rlp.LIST_HEADER_BYTE)
    for item in msg.access_list:
        rlp.write(sha, access_list_item(item))

    return sha.get_digest()


def _sign_digest(
    msg: EthereumSignTxEIP1559, keychain: Keychain, digest: bytes
) -> EthereumTxRequest:
    from trezor.crypto.curve import secp256k1
    from trezor.messages import EthereumTxRequest

    node = keychain.derive(msg.address_n)
    signature = secp256k1.sign(
        node.private_key(), digest, False, secp256k1.CANONICAL_SIG_ETHEREUM
    )

    req = EthereumTxRequest()
    req.signature_v = signature[0] - 27
    req.signature_r = signature[1:33]
    req.signature_s = signature[33:]

    return req
