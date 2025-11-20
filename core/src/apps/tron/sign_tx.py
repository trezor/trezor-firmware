from typing import TYPE_CHECKING

from trezor.wire import DataError

from apps.common.keychain import with_slip44_keychain

from . import CURVE, PATTERN, SLIP44_ID, consts

if TYPE_CHECKING:
    from trezor.messages import TronRawContract, TronSignature, TronSignTx

    from apps.common.keychain import Keychain


@with_slip44_keychain(PATTERN, slip44_id=SLIP44_ID, curve=CURVE)
async def sign_tx(msg: TronSignTx, keychain: Keychain) -> TronSignature:
    import trezor.messages as messages
    from trezor import TR
    from trezor.crypto.curve import secp256k1
    from trezor.crypto.hashlib import sha256
    from trezor.protobuf import dump_message_buffer
    from trezor.ui.layouts import confirm_blob, confirm_tron_tx, show_continue_in_app
    from trezor.wire.context import call_any

    from apps.common import paths

    from .helpers import address_from_public_key

    await paths.validate_path(keychain, msg.address_n)
    node = keychain.derive(msg.address_n)
    private_key = node.private_key()
    public_key = secp256k1.publickey(node.private_key(), False)
    trezor_address = address_from_public_key(public_key)

    if msg.data:
        if len(msg.data) > consts.MAX_DATA_LENGTH:
            raise DataError("Tron: data field too long")
        await confirm_blob("confirm_memo", TR.words__memo, msg.data)

    # Currently, Tron transactions only support a single contract call,
    # but they have defined the contract as a list for future expansion.
    # https://github.com/tronprotocol/protocol/blob/37bb922a9967bbbef1e84de1c9e5cda56a2d7998/core/Tron.proto#L439-L440
    contract = await call_any(messages.TronContractRequest(), *consts.contract_types)
    raw_contract, total_send = await process_contract(contract, trezor_address)  # type: ignore [Argument of type "MessageType" cannot be assigned to parameter "contract" of type "TronMessageType" in function "process_contract"]

    # Regarding the TransferContract, the maximum fee is currently not calculated;
    # I will research it further.
    await confirm_tron_tx(total_send, TR.words__unknown)

    raw_tx = messages.TronRawTransaction(
        ref_block_bytes=msg.ref_block_bytes,
        ref_block_hash=msg.ref_block_hash,
        expiration=msg.expiration,
        data=msg.data,
        contract=[raw_contract],
        timestamp=msg.timestamp,
        fee_limit=msg.fee_limit,
    )
    serialized_tx = dump_message_buffer(raw_tx)

    w_hash = sha256(serialized_tx).digest()
    signature = secp256k1.sign(private_key, w_hash, False)
    v_val = signature[0] + 27 if signature[0] < 27 else signature[0]
    signature = signature[1:] + bytes([v_val])

    show_continue_in_app(TR.send__transaction_signed)
    return messages.TronSignature(signature=signature)


async def process_contract(
    contract: consts.TronMessageType, trezor_address: str
) -> tuple[TronRawContract, str]:
    import trezor.messages as messages
    from trezor.enums import TronRawContractType
    from trezor.protobuf import dump_message_buffer

    from . import converter, layout

    total_send = parameter = contract_type = None

    if messages.TronTransferContract.is_type_of(contract):
        contract_type = TronRawContractType.TransferContract
        await layout.confirm_transfer_contract(contract, trezor_address)
        parameter = converter.convert_transfer_contract(contract)
        total_send = layout.format_trx_amount(contract.amount)
    else:
        raise DataError("Tron: contract type unknown")

    serialized_parameter = dump_message_buffer(parameter)
    raw_contract = messages.TronRawContract(
        type=contract_type,
        parameter=messages.TronRawParameter(
            type_url=consts.TYPE_URL_TEMPLATE
            + consts.get_contract_type_name(contract_type),
            value=serialized_parameter,
        ),
    )

    return raw_contract, total_send
