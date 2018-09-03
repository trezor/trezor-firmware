import ustruct

from trezor import wire
from trezor.crypto import hashlib
from trezor.messages import TezosContractType
from trezor.messages.TezosSignedTx import TezosSignedTx

from apps.common import seed
from apps.tezos.helpers import (
    b58cencode,
    check_sig_remove_first_byte,
    get_address_prefix,
    get_curve_module,
    get_curve_name,
    get_sig_prefix,
)
from apps.tezos.layout import *


async def tezos_sign_tx(ctx, msg):
    address_n = msg.address_n or ()
    curve = msg.curve or 0

    node = await seed.derive_node(ctx, address_n, get_curve_name(curve))

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
        delegate = _get_address_by_tag(msg.delegation.delegate)

        if source != delegate:
            await require_confirm_delegation_baker(ctx, delegate)
            await require_confirm_set_delegate(ctx, msg.delegation.fee)
        # if account registers itself as a delegate
        else:
            await require_confirm_register_delegate(ctx, source, msg.delegation.fee)

    else:
        raise wire.DataError("Invalid operation")

    opbytes = _get_operation_bytes(msg)

    watermark = bytes([3])
    wm_opbytes = watermark + opbytes
    wm_opbytes_hash = hashlib.blake2b(wm_opbytes, outlen=32).digest()

    curve_module = get_curve_module(curve)
    signature = curve_module.sign(node.private_key(), wm_opbytes_hash)

    if check_sig_remove_first_byte(curve):
        signature = signature[1:]

    sig_op_contents = opbytes + signature
    sig_op_contents_hash = hashlib.blake2b(sig_op_contents, outlen=32).digest()
    ophash = b58cencode(sig_op_contents_hash, prefix="o")

    sig_prefixed = b58cencode(signature, prefix=get_sig_prefix(curve))

    return TezosSignedTx(
        signature=sig_prefixed, sig_op_contents=sig_op_contents, operation_hash=ophash
    )


def _get_address_by_tag(address_hash):
    tag = int(address_hash[0])
    return b58cencode(address_hash[1:], prefix=get_address_prefix(tag))


def _get_address_from_contract(address):
    if address.tag == TezosContractType.Implicit:
        return _get_address_by_tag(address.hash)

    elif address.tag == TezosContractType.Originated:
        return b58cencode(address.hash[:-1], prefix="KT1")

    raise wire.DataError("Invalid contract type")


def _get_operation_bytes(msg):
    result = msg.branch

    # when the account sends first operation in lifetime,
    # we need to reveal its publickey
    if msg.reveal is not None:
        result += _encode_common(msg.reveal, "reveal")
        result += msg.reveal.public_key

    # transaction operation
    if msg.transaction is not None:
        result += _encode_common(msg.transaction, "transaction")
        result += _encode_zarith(msg.transaction.amount)
        result += _encode_contract_id(msg.transaction.destination)
        result += _encode_data_with_bool_prefix(msg.transaction.parameters)
    # origination operation
    elif msg.origination is not None:
        result += _encode_common(msg.origination, "origination")
        result += msg.origination.manager_pubkey
        result += _encode_zarith(msg.origination.balance)
        result += _encode_bool(msg.origination.spendable)
        result += _encode_bool(msg.origination.delegatable)
        result += _encode_data_with_bool_prefix(msg.origination.delegate)
        result += _encode_data_with_bool_prefix(msg.origination.script)
    # delegation operation
    elif msg.delegation is not None:
        result += _encode_common(msg.delegation, "delegation")
        result += _encode_data_with_bool_prefix(msg.delegation.delegate)

    return bytes(result)


def _encode_common(operation, str_operation):
    operation_tags = {"reveal": 7, "transaction": 8, "origination": 9, "delegation": 10}
    result = ustruct.pack("<b", operation_tags[str_operation])
    result += _encode_contract_id(operation.source)
    result += _encode_zarith(operation.fee)
    result += _encode_zarith(operation.counter)
    result += _encode_zarith(operation.gas_limit)
    result += _encode_zarith(operation.storage_limit)
    return result


def _encode_contract_id(contract_id):
    return ustruct.pack("<b", contract_id.tag) + contract_id.hash


def _encode_bool(boolean):
    return ustruct.pack("<b", 255) if boolean else ustruct.pack("<b", 0)


def _encode_data_with_bool_prefix(data):
    return _encode_bool(True) + data if data is not None else _encode_bool(False)


def _encode_zarith(num):
    result = bytes()

    while True:
        byte = num & 127
        num = num >> 7

        if num == 0:
            result += ustruct.pack("<b", byte)
            break

        result += ustruct.pack("<b", 128 | byte)

    return result
