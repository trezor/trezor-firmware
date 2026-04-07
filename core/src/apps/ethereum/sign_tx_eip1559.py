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

    from apps.common.keychain import Keychain

    from .definitions import Definitions


_TX_TYPE = const(2)


def access_list_item_length(item: EthereumAccessList) -> int:
    address_length = rlp.length(bytes_from_address(item.address))
    keys_length = rlp.length(item.storage_keys)
    return (
        rlp.header_length(address_length + keys_length) + address_length + keys_length
    )


@with_keychain_from_chain_id
async def sign_tx_eip1559(
    msg: EthereumSignTxEIP1559,
    keychain: Keychain,
    defs: Definitions,
) -> EthereumTxRequest:
    from trezor import TR, wire
    from trezor.crypto import rlp  # local_cache_global
    from trezor.crypto.hashlib import sha3_256
    from trezor.ui.layouts import show_continue_in_app
    from trezor.utils import HashWriter

    from apps.common import paths

    from .helpers import format_ethereum_amount, get_fee_items_eip1559
    from .sign_tx import (
        check_common_fields,
        confirm_tx_data,
        request_initial_data,
        send_request_chunk,
    )

    gas_limit = msg.gas_limit  # local_cache_attribute
    data_length = msg.data_length  # local_cache_attribute

    # check
    if len(msg.max_gas_fee) + len(gas_limit) > 30:
        raise wire.DataError("Fee overflow")
    if len(msg.max_priority_fee) + len(gas_limit) > 30:
        raise wire.DataError("Fee overflow")
    check_common_fields(msg)

    # have a user confirm signing
    await paths.validate_path(keychain, msg.address_n)
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

    sha = HashWriter(sha3_256(keccak=True))

    rlp.write(sha, _TX_TYPE)
    rlp.write_header(sha, _get_digest_length(msg, data_length), rlp.LIST_HEADER_BYTE)

    fields: tuple[rlp.RLPItem, ...] = (
        msg.chain_id,
        msg.nonce,
        msg.max_priority_fee,
        msg.max_gas_fee,
        gas_limit,
        address_bytes,
        msg.value,
    )
    for field in fields:
        rlp.write(sha, field)

    initial_data = await request_initial_data(msg, sha)

    confirm_data_chunk, confirm_summary = await confirm_tx_data(
        initial_data,
        msg,
        defs,
        None,
        address_bytes,
        maximum_fee,
        fee_items,
        payment_req_verifier,
    )

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

    # write_access_list
    payload_length = sum(access_list_item_length(i) for i in msg.access_list)
    rlp.write_header(sha, payload_length, rlp.LIST_HEADER_BYTE)
    for item in msg.access_list:
        address_bytes = bytes_from_address(item.address)
        address_length = rlp.length(address_bytes)
        keys_length = rlp.length(item.storage_keys)
        rlp.write_header(sha, address_length + keys_length, rlp.LIST_HEADER_BYTE)
        rlp.write(sha, address_bytes)
        rlp.write(sha, item.storage_keys)

    digest = sha.get_digest()

    # transaction data confirmed, proceed with signing
    result = _sign_digest(msg, keychain, digest)

    show_continue_in_app(TR.send__transaction_signed)
    return result


def _get_digest_length(msg: EthereumSignTxEIP1559, data_length: int) -> int:
    length = 0

    fields: tuple[rlp.RLPItem, ...] = (
        msg.nonce,
        msg.gas_limit,
        bytes_from_address(msg.to),
        msg.value,
        msg.chain_id,
        msg.max_gas_fee,
        msg.max_priority_fee,
    )
    for field in fields:
        length += rlp.length(field)

    length += rlp.header_length(data_length, msg.data_initial_chunk)
    length += data_length

    # access_list_length
    payload_length = sum(access_list_item_length(i) for i in msg.access_list)
    access_list_length = rlp.header_length(payload_length) + payload_length

    length += access_list_length

    return length


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
