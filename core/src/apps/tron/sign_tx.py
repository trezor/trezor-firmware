from micropython import const
from typing import TYPE_CHECKING

from trezor import messages
from trezor.protobuf import dump_message_buffer
from trezor.wire import DataError

from apps.common.keychain import with_slip44_keychain

from . import CURVE, PATTERN, SLIP44_ID, consts, layout

if TYPE_CHECKING:
    from trezor.messages import TronRawContract, TronSignature, TronSignTx
    from trezor.protobuf import MessageType

    from apps.common.keychain import Keychain


@with_slip44_keychain(PATTERN, slip44_id=SLIP44_ID, curve=CURVE)
async def sign_tx(msg: TronSignTx, keychain: Keychain) -> TronSignature:
    from trezor import TR
    from trezor.crypto.curve import secp256k1
    from trezor.crypto.hashlib import sha256
    from trezor.ui.layouts import confirm_blob, confirm_tron_send, show_continue_in_app
    from trezor.wire.context import call_any

    from apps.common import paths

    _MAX_DATA_LENGTH = const(256)
    _MAX_FEE_LIMIT = const(15_000_000_000)  # TRON: Maximum Fee limit in SUN.

    await paths.validate_path(keychain, msg.address_n)
    node = keychain.derive(msg.address_n)

    # It is also not necessary for it to be UTF-8 encoded but all applications using it use it as a Note to be attached with the transaction.
    if msg.data and msg.data != b"":
        if len(msg.data) > _MAX_DATA_LENGTH:
            raise DataError("Tron: data field too long")
        await confirm_blob(
            "confirm_tx_note",
            TR.words__note,
            bytes(msg.data).decode("utf-8", "replace"),
            chunkify=False,
        )

    # https://developers.tron.network/docs/set-feelimit
    fee_limit = msg.fee_limit or 0
    if fee_limit > _MAX_FEE_LIMIT:
        raise DataError("Tron: fees too high")

    contract = await call_any(messages.TronContractRequest(), *consts.CONTRACT_TYPES)
    raw_contract, total_send = await process_contract(contract)

    fee_string = (
        layout.format_energy_amount(fee_limit)
        if messages.TronTriggerSmartContract.is_type_of(contract)
        else None
    )
    await confirm_tron_send(total_send, fee_string)

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

    # https://tronprotocol.github.io/documentation-en/mechanism-algorithm/account/#algorithm
    signature = secp256k1.sign(node.private_key(), w_hash, False)
    signature = signature[1:65] + signature[0:1]  # r || s || v

    show_continue_in_app(TR.send__transaction_signed)
    return messages.TronSignature(signature=signature)


async def process_contract(
    contract: MessageType,
) -> tuple[TronRawContract, str | None]:
    from trezor.enums import TronRawContractType

    total_send = None
    if messages.TronTransferContract.is_type_of(contract):
        contract_type = TronRawContractType.TransferContract
        await layout.confirm_transfer_contract(contract)
        total_send = layout.format_trx_amount(contract.amount)
    elif messages.TronTriggerSmartContract.is_type_of(contract):
        contract_type = TronRawContractType.TriggerSmartContract
        await layout.confirm_unkown_smart_contract(contract)
        # TODO: Extract from contract.data to total_send
    else:
        raise DataError("Tron: contract type unknown")

    serialized_parameter = dump_message_buffer(contract)
    raw_contract = messages.TronRawContract(
        type=contract_type,
        parameter=messages.TronRawParameter(
            type_url=consts.TYPE_URL_TEMPLATE
            + consts.get_contract_type_name(contract_type),
            value=serialized_parameter,
        ),
    )

    return raw_contract, total_send
