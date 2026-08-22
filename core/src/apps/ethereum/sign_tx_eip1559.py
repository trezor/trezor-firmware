from micropython import const
from typing import TYPE_CHECKING

from trezor.crypto import rlp

from .helpers import bytes_from_address
from .keychain import with_keychain_from_chain_id

if TYPE_CHECKING:
    from trezor.crypto import bip32
    from trezor.messages import (
        EthereumAccessList,
        EthereumAuth7702Tuple,
        EthereumSignTxEIP1559,
        EthereumTxRequest,
    )
    from trezor.utils import HashWriter

    from apps.common.keychain import Keychain

    from .definitions import Definitions


_EIP1559_TX_TYPE = const(2)  # used for signing EIP-1559 transactions

_EIP7702_TX_TYPE = const(4)  # used for signing EIP-7702 transactions
_EIP7702_TUPLE_MAGIC = const(5)  # used for signing EIP-7702 authorization tuples


def access_list_item(item: EthereumAccessList) -> rlp.RLPItem:
    return [bytes_from_address(item.address), item.storage_keys]


@with_keychain_from_chain_id
async def sign_tx_eip1559(
    msg: EthereumSignTxEIP1559,
    keychain: Keychain,
    defs: Definitions,
) -> EthereumTxRequest:
    from trezor import TR
    from trezor.ui.layouts import show_continue_in_app
    from trezor.wire import DataError

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
        raise DataError("Fee overflow")
    if len(msg.max_priority_fee) + len(gas_limit) > 30:
        raise DataError("Fee overflow")
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

    # Confirm and sign EIP-7702 delegation (may raise on unsupported requests)
    auth7702_list: list[EthereumAuth7702Tuple] = await _handle_eip7702(
        msg,
        keychain,
        defs,
    )
    auth7702_rlp: rlp.RLPList = [i.items for i in auth7702_list]

    payment_req_verifier = None
    if msg.payment_req:
        from apps.common.payment_request import PaymentRequestVerifier

        slip44_id = paths.unharden(msg.address_n[1])
        payment_req_verifier = PaymentRequestVerifier(
            msg.payment_req, slip44_id, keychain, amount_size_bytes=32
        )

    sha = _start_digest(msg, auth7702_rlp)
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

    digest = _finish_digest(msg, auth7702_rlp, sha)

    # transaction data confirmed, proceed with signing
    result = _sign_digest(msg, keychain, digest)

    # EIP-7702 authorization list (if not empty)
    if auth7702_list:
        result.auth7702_list = auth7702_list

    show_continue_in_app(TR.send__transaction_signed)
    return result


def _start_digest(msg: EthereumSignTxEIP1559, auth7702_rlp: rlp.RLPList) -> HashWriter:
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

    tx_type = _EIP1559_TX_TYPE
    # EIP-7702 authorization list (if not empty)
    if auth7702_rlp:
        length += rlp.length(auth7702_rlp)
        tx_type = _EIP7702_TX_TYPE

    # hash only `_TX_TYPE`, RLP header and `fields` (see above).
    # calldata and access_list will be hashed later.
    sha = keccak256()
    # different transaction type is used for EIP-7702 authorization
    sha.append(tx_type)

    rlp.write_header(sha, length, rlp.LIST_HEADER_BYTE)
    for field in fields:
        rlp.write(sha, field)
    return sha


def _finish_digest(
    msg: EthereumSignTxEIP1559, auth7702_rlp: rlp.RLPList, sha: HashWriter
) -> bytes:
    # write_access list (streaming instead of full materialization)
    payload_length = sum(rlp.length(access_list_item(i)) for i in msg.access_list)
    rlp.write_header(sha, payload_length, rlp.LIST_HEADER_BYTE)
    for item in msg.access_list:
        rlp.write(sha, access_list_item(item))

    # EIP-7702 authorization list (if not empty)
    if auth7702_rlp:
        rlp.write(sha, auth7702_rlp)

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


async def _handle_eip7702(
    msg: EthereumSignTxEIP1559,
    keychain: Keychain,
    defs: Definitions,
) -> list[EthereumAuth7702Tuple]:

    if msg.auth7702 is None:
        return []  # no EIP-7702 authorization tuples

    from trezor import TR
    from trezor.ui import layouts
    from trezor.wire import DataError

    from apps.common import paths

    from .helpers import bytes_from_address, get_account_and_path
    from .networks import UNKNOWN_NETWORK
    from .sc_constants import lookup_eip7702_address

    address_n = msg.address_n
    await paths.validate_path(keychain, address_n)

    chain_id = msg.chain_id
    if chain_id == 0:
        raise DataError("EIP-7702: cross-chain delegation")
    if not msg.to:
        raise DataError("EIP-7702: empty destination")
    if msg.data_length:
        raise DataError("EIP-7702: non-empty calldata")
    if msg.payment_req is not None:
        raise DataError("EIP-7702: unsupported payment request")
    if int.from_bytes(msg.value, "big") != 0:
        raise DataError("EIP-7702: non-zero value")

    if defs.network is UNKNOWN_NETWORK:
        raise DataError("EIP-7702: unknown network")

    # authorization tuple nonce must be (tx.nonce + 1)
    nonce = int.from_bytes(msg.nonce, "big") + 1
    if nonce >= 0xFFFFFFFFFFFFFFFF:
        raise DataError("EIP-7702: invalid nonce")

    account, account_path = get_account_and_path(address_n)
    if account is None or account_path is None:
        raise DataError("Unknown account")

    network_item = (TR.ethereum__network, defs.network.name, None)
    delegate_addr = msg.auth7702.delegate
    delegate_bytes = bytes_from_address(delegate_addr)
    if delegate_bytes == b"\x00" * 20:  # -> revocation
        await layouts.confirm_ethereum_eip7702_revoke(
            network_item=network_item,
            account=account,
            account_path=account_path,
            nonce=nonce,
        )
    else:
        delegate_name = lookup_eip7702_address(chain_id, delegate_bytes)
        if delegate_name is None:
            raise DataError("Unknown EIP-7702 delegate address")

        await layouts.confirm_ethereum_eip7702_auth(
            delegate_name=delegate_name,
            delegate_addr=delegate_addr,
            network_item=network_item,
            account=account,
            account_path=account_path,
            nonce=nonce,
        )

    return [
        _sign_eip7702_tuple(keychain.derive(address_n), chain_id, delegate_bytes, nonce)
    ]


def _sign_eip7702_tuple(
    node: bip32.HDNode, chain_id: int, delegate_bytes: bytes, nonce: int
) -> EthereumAuth7702Tuple:
    from trezor.crypto.curve import secp256k1
    from trezor.messages import EthereumAuth7702Tuple

    from .helpers import keccak256

    sha = keccak256()
    sha.append(_EIP7702_TUPLE_MAGIC)

    fields: rlp.RLPList = [chain_id, delegate_bytes, nonce]
    rlp.write(sha, fields)
    digest = sha.get_digest()

    signature = secp256k1.sign(
        node.private_key(), digest, False, secp256k1.CANONICAL_SIG_ETHEREUM
    )
    # EIP-7702 authorization tuple: [chain_id, delegate, nonce, y_parity, r, s]
    # type SetCodeAuthorization struct {
    #   ChainID uint256.Int
    #   Address common.Address
    #   Nonce   uint64
    #   V       uint8
    #   R       uint256.Int
    #   S       uint256.Int
    # }
    y_parity: int = signature[0] - 27
    r = int.from_bytes(signature[1:33], "big")
    s = int.from_bytes(signature[33:], "big")

    # Note: integers must be minimally encoded into bytestrings for RLP serialization:
    return EthereumAuth7702Tuple(
        items=[
            rlp.int_to_bytes(chain_id),
            delegate_bytes,
            rlp.int_to_bytes(nonce),
            rlp.int_to_bytes(y_parity),
            rlp.int_to_bytes(r),
            rlp.int_to_bytes(s),
        ]
    )
