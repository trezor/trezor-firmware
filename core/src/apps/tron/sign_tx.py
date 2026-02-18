from micropython import const
from typing import TYPE_CHECKING

from trezor import messages
from trezor.protobuf import dump_message_buffer
from trezor.wire import DataError

from apps.common.keychain import with_slip44_keychain

from . import CURVE, PATTERN, SLIP44_ID, consts, layout

if TYPE_CHECKING:
    from buffer_types import AnyBytes
    from typing import Tuple

    from trezor.messages import (
        TronRawContract,
        TronSignature,
        TronSignTx,
        TronTriggerSmartContract,
    )
    from trezor.protobuf import MessageType

    from apps.common.keychain import Keychain


@with_slip44_keychain(PATTERN, slip44_id=SLIP44_ID, curve=CURVE)
async def sign_tx(msg: TronSignTx, keychain: Keychain) -> TronSignature:
    from trezor import TR
    from trezor.crypto.curve import secp256k1
    from trezor.crypto.hashlib import sha256
    from trezor.ui.layouts import confirm_blob, show_continue_in_app
    from trezor.wire.context import call_any

    from apps.common import paths

    _MAX_DATA_LENGTH = const(256)
    _MAX_FEE_LIMIT = const(15_000_000_000)  # TRON: Maximum Fee limit in SUN.

    await paths.validate_path(keychain, msg.address_n)
    node = keychain.derive(msg.address_n)

    # It is not necessary for it to be UTF-8 encoded but all applications using it use it as a Note to be attached with the transaction.
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
    raw_contract = await process_contract(contract, fee_limit)

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
    fee_limit: int,
) -> TronRawContract:

    # Importing individual enums would de-clutter the code a bit.
    # But it causes type error in messages.TronRawContract.type.
    from trezor import TR
    from trezor.enums import TronRawContractType
    from trezor.ui.layouts import confirm_tron_send

    _INT64_MAX = const(9_223_372_036_854_775_807)

    if messages.TronTransferContract.is_type_of(contract):
        contract_type = TronRawContractType.TransferContract
        await layout.confirm_transfer_contract(contract)
        if contract.amount > _INT64_MAX:
            raise DataError("Tron: invalid transfer amount")
        await confirm_tron_send(layout.format_trx_amount(contract.amount), None)

    elif messages.TronTriggerSmartContract.is_type_of(contract):
        contract_type = TronRawContractType.TriggerSmartContract
        await process_smart_contract(contract, fee_limit)

    elif messages.TronFreezeBalanceV2Contract.is_type_of(contract):
        from trezor.enums import TronResourceCode

        contract_type = TronRawContractType.FreezeBalanceV2Contract

        await layout.confirm_freeze_operations(
            owner_address=contract.owner_address,
            balance=contract.balance,
            resource=contract.resource,
            title=TR.ethereum__staking_stake,
        )

        # TRON protocol uses proto3, which omits fields with default values from
        # serialization. Since BANDWIDTH=0 is the default, we must set resource=None
        # to match proto3 encoding and produce the correct transaction hash.
        if contract.resource == TronResourceCode.BANDWIDTH:
            contract = messages.TronFreezeBalanceV2Contract(
                owner_address=contract.owner_address,
                balance=contract.balance,
                resource=None,
            )
    elif messages.TronUnfreezeBalanceV2Contract.is_type_of(contract):
        from trezor.enums import TronResourceCode

        contract_type = TronRawContractType.UnfreezeBalanceV2Contract

        await layout.confirm_freeze_operations(
            owner_address=contract.owner_address,
            balance=contract.balance,
            resource=contract.resource,
            title=TR.ethereum__staking_unstake,
        )

        if contract.resource == TronResourceCode.BANDWIDTH:
            contract = messages.TronUnfreezeBalanceV2Contract(
                owner_address=contract.owner_address,
                balance=contract.balance,
                resource=None,
            )

    elif messages.TronWithdrawUnfreeze.is_type_of(contract):
        contract_type = TronRawContractType.WithdrawExpireUnfreezeContract
        await layout.confirm_withdraw_unfreeze(contract.owner_address)

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

    return raw_contract


async def process_smart_contract(
    contract: TronTriggerSmartContract, fee_limit: int
) -> None:
    if await process_known_trc20_contract(contract, fee_limit):
        return
    else:
        await layout.confirm_unknown_smart_contract(contract, fee_limit)


async def process_known_trc20_contract(
    contract: TronTriggerSmartContract, fee_limit: int
) -> bool:
    """Returns False when the contract is unrecoginsed. i.e. not (Transfer and known TRC-20)"""
    from trezor.utils import BufferReader

    from .sc_constants import (
        SC_ARGUMENT_ADDRESS_BYTES,
        SC_ARGUMENT_BYTES,
        SC_FUNC_SIG_APPROVE,
        SC_FUNC_SIG_BYTES,
        SC_FUNC_SIG_TRANSFER,
    )

    token_info = get_token_info(contract.contract_address)
    if token_info is None or len(contract.data) != 68:
        return False

    token_decimals, token_symbol = token_info

    data_reader = BufferReader(contract.data)
    func_sig = data_reader.read_memoryview(SC_FUNC_SIG_BYTES)
    if func_sig not in (SC_FUNC_SIG_APPROVE, SC_FUNC_SIG_TRANSFER):
        return False

    if data_reader.remaining_count() < SC_ARGUMENT_BYTES * 2:
        return False

    address_arg = data_reader.read_memoryview(SC_ARGUMENT_BYTES)
    assert all(
        byte == 0
        for byte in address_arg[: SC_ARGUMENT_BYTES - SC_ARGUMENT_ADDRESS_BYTES]
    )

    # TRON truncates the mandatory prefix \x41 from addresses in data
    recipient = b"\x41" + bytes(
        address_arg[SC_ARGUMENT_BYTES - SC_ARGUMENT_ADDRESS_BYTES :]
    )

    amount_arg = data_reader.read_memoryview(SC_ARGUMENT_BYTES)

    await layout.confirm_known_trc20_smart_contract(
        func_sig == SC_FUNC_SIG_APPROVE,
        recipient,
        amount_arg,
        fee_limit,
        token_decimals,
        token_symbol,
    )
    return True


def get_token_info(token_address: AnyBytes) -> Tuple[int, str] | None:
    for address, decimals, symbol in consts.token_iterator():
        if token_address == address:
            return decimals, symbol
    return None
