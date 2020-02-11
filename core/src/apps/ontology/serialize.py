from trezor.messages import OntologyAsset
from trezor.messages.OntologyOntIdAddAttributes import OntologyOntIdAddAttributes
from trezor.messages.OntologyOntIdRegister import OntologyOntIdRegister
from trezor.messages.OntologyTransaction import OntologyTransaction
from trezor.messages.OntologyTransfer import OntologyTransfer
from trezor.messages.OntologyTxAttribute import OntologyTxAttribute
from trezor.messages.OntologyWithdrawOng import OntologyWithdrawOng

from . import const as Const, writer
from .helpers import get_bytes_from_address
from .sc.native_builder import ParamStruct, build_native_call


def serialize_tx(tx: OntologyTransaction, payload: bytes, hw) -> None:
    writer.write_byte(hw, tx.version)
    writer.write_byte(hw, Const.TRANSACTION_TYPE)
    writer.write_uint32(hw, tx.nonce)
    writer.write_uint64(hw, tx.gas_price)
    writer.write_uint64(hw, tx.gas_limit)
    payer = get_bytes_from_address(tx.payer)
    writer.write_bytes(hw, payer)

    writer.write_bytes_with_length(hw, payload)

    attributes = tx.tx_attributes
    writer.write_varint(hw, len(attributes))

    if attributes is not None:
        for attribute in attributes:
            _serialize_tx_attribute(hw, attribute)


def serialize_transfer(transfer: OntologyTransfer) -> bytes:
    from_address = get_bytes_from_address(transfer.from_address)
    to_address = get_bytes_from_address(transfer.to_address)
    amount = transfer.amount
    contract = ""

    if transfer.asset == OntologyAsset.ONT:
        contract = Const.ONT_CONTRACT
    else:
        contract = Const.ONG_CONTRACT

    struct = ParamStruct([from_address, to_address, amount])
    native_call = build_native_call("transfer", [[struct]], contract)

    return native_call


def serialize_withdraw_ong(withdraw_ong: OntologyWithdrawOng) -> bytes:
    from_address = get_bytes_from_address(withdraw_ong.from_address)
    to_address = get_bytes_from_address(withdraw_ong.to_address)
    amount = withdraw_ong.amount

    struct = ParamStruct([from_address, Const.ONT_CONTRACT, to_address, amount])
    native_call = build_native_call("transferFrom", [struct], Const.ONG_CONTRACT)

    return native_call


def serialize_ont_id_register(register: OntologyOntIdRegister) -> bytes:
    ont_id = register.ont_id.encode()

    struct = ParamStruct([ont_id, register.public_key])
    native_call = build_native_call(
        "regIDWithPublicKey", [struct], Const.ONTID_CONTRACT
    )

    return native_call


def serialize_ont_id_add_attributes(add: OntologyOntIdAddAttributes) -> bytes:
    ont_id = add.ont_id.encode()
    attributes = add.ont_id_attributes

    arguments = [ont_id, len(attributes)]

    for attribute in attributes:
        arguments.append(attribute.key.encode())
        arguments.append(attribute.type.encode())
        arguments.append(attribute.value.encode())

    arguments.append(add.public_key)

    struct = ParamStruct(arguments)
    native_call = build_native_call("addAttributes", [struct], Const.ONTID_CONTRACT)

    return native_call


def _serialize_tx_attribute(ret: bytearray, attribute: OntologyTxAttribute) -> None:
    writer.write_byte(ret, attribute.usage)

    if attribute.data is not None:
        writer.write_bytes_with_length(ret, attribute.data)
