from trezor import wire
from trezor.crypto import hashlib
from trezor.crypto.curve import ed25519
from trezor.messages import TezosContractType
from trezor.messages.TezosSignedTx import TezosSignedTx

from apps.common import seed
from apps.common.writers import write_bytes, write_uint8
from apps.tezos.helpers import (
    TEZOS_CURVE,
    TEZOS_ORIGINATED_ADDRESS_PREFIX,
    TEZOS_SIGNATURE_PREFIX,
    base58_encode_check,
)
from apps.tezos.layout import *


async def sign_tx(ctx, msg):
    address_n = msg.address_n or ()
    node = await seed.derive_node(ctx, address_n, TEZOS_CURVE)

    if msg.transaction is not None:
        to = _get_address_from_contract(msg.transaction.destination)
        await require_confirm_tx(ctx, to, msg.transaction.amount)
        await require_confirm_fee(ctx, msg.transaction.amount, msg.transaction.fee)

    elif msg.origination is not None:
        source = _get_address_from_contract(msg.origination.source)
        await require_confirm_origination(ctx, source)
        await require_confirm_origination_fee(
            ctx, msg.origination.balance, msg.origination.fee
        )

    elif msg.delegation is not None:
        source = _get_address_from_contract(msg.delegation.source)

        delegate = None
        if msg.delegation.delegate is not None:
            delegate = _get_address_by_tag(msg.delegation.delegate)

        if delegate is not None and source != delegate:
            await require_confirm_delegation_baker(ctx, delegate)
            await require_confirm_set_delegate(ctx, msg.delegation.fee)
        # if account registers itself as a delegate
        else:
            await require_confirm_register_delegate(ctx, source, msg.delegation.fee)

    else:
        raise wire.DataError("Invalid operation")

    w = bytearray()
    _get_operation_bytes(w, msg)

    opbytes = bytes(w)

    # watermark 0x03 is prefix for transactions, delegations, originations, reveals...
    watermark = bytes([3])
    wm_opbytes = watermark + opbytes
    wm_opbytes_hash = hashlib.blake2b(wm_opbytes, outlen=32).digest()

    signature = ed25519.sign(node.private_key(), wm_opbytes_hash)

    sig_op_contents = opbytes + signature
    sig_op_contents_hash = hashlib.blake2b(sig_op_contents, outlen=32).digest()
    ophash = base58_encode_check(sig_op_contents_hash, prefix="o")

    sig_prefixed = base58_encode_check(signature, prefix=TEZOS_SIGNATURE_PREFIX)

    return TezosSignedTx(
        signature=sig_prefixed, sig_op_contents=sig_op_contents, operation_hash=ophash
    )


def _get_address_by_tag(address_hash):
    prefixes = ["tz1", "tz2", "tz3"]
    tag = int(address_hash[0])

    if 0 <= tag < len(prefixes):
        return base58_encode_check(address_hash[1:], prefix=prefixes[tag])
    raise wire.DataError("Invalid tag in address hash")


def _get_address_from_contract(address):
    if address.tag == TezosContractType.Implicit:
        return _get_address_by_tag(address.hash)

    elif address.tag == TezosContractType.Originated:
        return base58_encode_check(
            address.hash[:-1], prefix=TEZOS_ORIGINATED_ADDRESS_PREFIX
        )

    raise wire.DataError("Invalid contract type")


def _get_operation_bytes(w: bytearray, msg):
    write_bytes(w, msg.branch)

    # when the account sends first operation in lifetime,
    # we need to reveal its publickey
    if msg.reveal is not None:
        _encode_common(w, msg.reveal, "reveal")
        write_bytes(w, msg.reveal.public_key)

    # transaction operation
    if msg.transaction is not None:
        _encode_common(w, msg.transaction, "transaction")
        _encode_zarith(w, msg.transaction.amount)
        _encode_contract_id(w, msg.transaction.destination)
        _encode_data_with_bool_prefix(w, msg.transaction.parameters)
    # origination operation
    elif msg.origination is not None:
        _encode_common(w, msg.origination, "origination")
        write_bytes(w, msg.origination.manager_pubkey)
        _encode_zarith(w, msg.origination.balance)
        _encode_bool(w, msg.origination.spendable)
        _encode_bool(w, msg.origination.delegatable)
        _encode_data_with_bool_prefix(w, msg.origination.delegate)
        _encode_data_with_bool_prefix(w, msg.origination.script)
    # delegation operation
    elif msg.delegation is not None:
        _encode_common(w, msg.delegation, "delegation")
        _encode_data_with_bool_prefix(w, msg.delegation.delegate)


def _encode_common(w: bytearray, operation, str_operation):
    operation_tags = {"reveal": 7, "transaction": 8, "origination": 9, "delegation": 10}
    write_uint8(w, operation_tags[str_operation])
    _encode_contract_id(w, operation.source)
    _encode_zarith(w, operation.fee)
    _encode_zarith(w, operation.counter)
    _encode_zarith(w, operation.gas_limit)
    _encode_zarith(w, operation.storage_limit)


def _encode_contract_id(w: bytearray, contract_id):
    write_uint8(w, contract_id.tag)
    write_bytes(w, contract_id.hash)


def _encode_bool(w: bytearray, boolean):
    if boolean:
        write_uint8(w, 255)
    else:
        write_uint8(w, 0)


def _encode_data_with_bool_prefix(w: bytearray, data):
    if data:
        _encode_bool(w, True)
        write_bytes(w, data)
    else:
        _encode_bool(w, False)


def _encode_zarith(w: bytearray, num):
    while True:
        byte = num & 127
        num = num >> 7

        if num == 0:
            write_uint8(w, byte)
            break

        write_uint8(w, 128 | byte)
