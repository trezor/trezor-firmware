from micropython import const
from typing import TYPE_CHECKING

from trezor.crypto import rlp

from .helpers import bytes_from_address
from .keychain import with_keychain_from_chain_id

if TYPE_CHECKING:
    from trezor.messages import (
        EthereumSignTxEIP1559,
        EthereumAccessList,
        EthereumTxRequest,
    )

    from apps.common.keychain import Keychain
    from trezor.wire import Context


_TX_TYPE = const(2)


def access_list_item_length(item: EthereumAccessList) -> int:
    address_length = rlp.length(bytes_from_address(item.address))
    keys_length = rlp.length(item.storage_keys)
    return (
        rlp.header_length(address_length + keys_length) + address_length + keys_length
    )


@with_keychain_from_chain_id
async def sign_tx_eip1559(
    ctx: Context, msg: EthereumSignTxEIP1559, keychain: Keychain
) -> EthereumTxRequest:
    from trezor.crypto.hashlib import sha3_256
    from trezor.utils import HashWriter
    from trezor import wire
    from trezor.crypto import rlp  # local_cache_global
    from apps.common import paths
    from .layout import (
        require_confirm_data,
        require_confirm_eip1559_fee,
        require_confirm_tx,
    )
    from .sign_tx import handle_erc20, send_request_chunk, check_common_fields

    gas_limit = msg.gas_limit  # local_cache_attribute

    # check
    if len(msg.max_gas_fee) + len(gas_limit) > 30:
        raise wire.DataError("Fee overflow")
    if len(msg.max_priority_fee) + len(gas_limit) > 30:
        raise wire.DataError("Fee overflow")
    check_common_fields(msg)

    await paths.validate_path(ctx, keychain, msg.address_n)

    # Handle ERC20s
    token, address_bytes, recipient, value = await handle_erc20(ctx, msg)

    data_total = msg.data_length

    await require_confirm_tx(ctx, recipient, value, msg.chain_id, token)
    if token is None and msg.data_length > 0:
        await require_confirm_data(ctx, msg.data_initial_chunk, data_total)

    await require_confirm_eip1559_fee(
        ctx,
        value,
        int.from_bytes(msg.max_priority_fee, "big"),
        int.from_bytes(msg.max_gas_fee, "big"),
        int.from_bytes(gas_limit, "big"),
        msg.chain_id,
        token,
    )

    data = bytearray()
    data += msg.data_initial_chunk
    data_left = data_total - len(msg.data_initial_chunk)

    total_length = _get_total_length(msg, data_total)

    sha = HashWriter(sha3_256(keccak=True))

    rlp.write(sha, _TX_TYPE)

    rlp.write_header(sha, total_length, rlp.LIST_HEADER_BYTE)

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

    if data_left == 0:
        rlp.write(sha, data)
    else:
        rlp.write_header(sha, data_total, rlp.STRING_HEADER_BYTE, data)
        sha.extend(data)

    while data_left > 0:
        resp = await send_request_chunk(ctx, data_left)
        data_left -= len(resp.data_chunk)
        sha.extend(resp.data_chunk)

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
    result = _sign_digest(msg, keychain, digest)

    return result


def _get_total_length(msg: EthereumSignTxEIP1559, data_total: int) -> int:
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

    length += rlp.header_length(data_total, msg.data_initial_chunk)
    length += data_total

    # access_list_length
    payload_length = sum(access_list_item_length(i) for i in msg.access_list)
    access_list_length = rlp.header_length(payload_length) + payload_length

    length += access_list_length

    return length


def _sign_digest(
    msg: EthereumSignTxEIP1559, keychain: Keychain, digest: bytes
) -> EthereumTxRequest:
    from trezor.messages import EthereumTxRequest
    from trezor.crypto.curve import secp256k1

    node = keychain.derive(msg.address_n)
    signature = secp256k1.sign(
        node.private_key(), digest, False, secp256k1.CANONICAL_SIG_ETHEREUM
    )

    req = EthereumTxRequest()
    req.signature_v = signature[0] - 27
    req.signature_r = signature[1:33]
    req.signature_s = signature[33:]

    return req
