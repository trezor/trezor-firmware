from ubinascii import unhexlify

from trezor import wire
from trezor.crypto.curve import secp256k1
from trezor.crypto.hashlib import sha256
from trezor.messages.TronSignedTx import TronSignedTx
from trezor.messages.TronSignTx import TronSignTx

from apps.common import paths
from apps.tron import CURVE, TRON_PUBLICKEY, layout, tokens
from apps.tron.address import get_address_from_public_key, validate_full_path
from apps.tron.serialize import serialize
from apps.tron.address import _address_base58


async def sign_tx(ctx, msg: TronSignTx, keychain):
    """Parse and sign TRX transaction"""

    validate(msg)
    address_n = msg.address_n or ()
    await paths.validate_path(ctx, validate_full_path, keychain, address_n, CURVE)

    node = keychain.derive(address_n)

    seckey = node.private_key()
    public_key = secp256k1.publickey(seckey, False)
    address = get_address_from_public_key(public_key[:65])

    try:
        await _require_confirm_by_type(ctx, msg, address)
    except AttributeError:
        raise wire.DataError("The transaction has invalid asset data field")

    raw_data = serialize(msg, address)
    data_hash = sha256(raw_data).digest()

    signature = secp256k1.sign(seckey, data_hash, False)

    signature = signature[1:65] + bytes([~signature[0] & 0x01])
    return TronSignedTx(signature=signature, serialized_tx=raw_data)


async def _require_confirm_by_type(ctx, transaction, owner_address):
    """Confirm extra data if exist"""
    if transaction.data:
        await layout.require_confirm_data(ctx, transaction.data)

    """Confirm transaction"""
    contract = transaction.contract
    if contract.transfer_contract:
        return await layout.require_confirm_tx(
            ctx,
            contract.transfer_contract.to_address,
            contract.transfer_contract.amount,
        )

    if contract.transfer_asset_contract:
        if not validateToken(
            contract.transfer_asset_contract.asset_id,
            contract.transfer_asset_contract.asset_name,
            contract.transfer_asset_contract.asset_decimals,
            contract.transfer_asset_contract.asset_signature,
        ):
            raise wire.ProcessError("Token signature not valid")
        return await layout.require_confirm_tx_asset(
            ctx,
            contract.transfer_asset_contract.asset_name,
            contract.transfer_asset_contract.to_address,
            contract.transfer_asset_contract.amount,
            contract.transfer_asset_contract.asset_decimals,
        )

    if contract.vote_witness_contract:
        # count votes
        votes_addr = 0
        votes_total = 0
        for i in range(len(contract.vote_witness_contract.votes)):
            votes_addr += 1
            votes_total += contract.vote_witness_contract.votes[i].vote_count
        return await layout.require_confirm_vote_witness(ctx, votes_addr, votes_total)

    if contract.witness_create_contract:
        return await layout.require_confirm_witness_contract(
            ctx, contract.witness_create_contract.url
        )

    if contract.asset_issue_contract:
        if contract.asset_issue_contract.precision is None:
            contract.asset_issue_contract.precision = 0
        return await layout.require_confirm_asset_issue(
            ctx,
            contract.asset_issue_contract.name,
            contract.asset_issue_contract.abbr,
            contract.asset_issue_contract.total_supply,
            contract.asset_issue_contract.trx_num,
            contract.asset_issue_contract.num,
            contract.asset_issue_contract.precision,
        )

    if contract.witness_update_contract:
        return await layout.require_confirm_witness_update(
            ctx,
            str(owner_address, "utf-8"),
            contract.witness_update_contract.update_url,
        )

    if contract.participate_asset_issue_contract:
        if not validateToken(
            contract.participate_asset_issue_contract.asset_id,
            contract.participate_asset_issue_contract.asset_name,
            contract.participate_asset_issue_contract.asset_decimals,
            contract.participate_asset_issue_contract.asset_signature,
        ):
            raise wire.ProcessError("Token signature not valid")
        return await layout.require_confirm_participate_asset(
            ctx,
            contract.participate_asset_issue_contract.asset_name,
            contract.participate_asset_issue_contract.amount,
            contract.participate_asset_issue_contract.asset_decimals,
        )

    if contract.account_update_contract:
        return await layout.require_confirm_account_update(
            ctx, contract.account_update_contract.account_name
        )

    if contract.freeze_balance_contract:
        return await layout.require_confirm_freeze_balance(
            ctx,
            contract.freeze_balance_contract.frozen_balance,
            contract.freeze_balance_contract.frozen_duration,
            contract.freeze_balance_contract.resource,
            contract.freeze_balance_contract.receiver_address,
        )

    if contract.unfreeze_balance_contract:
        return await layout.require_confirm_unfreeze_balance(
            ctx,
            contract.unfreeze_balance_contract.resource,
            contract.unfreeze_balance_contract.receiver_address,
        )

    if contract.withdraw_balance_contract:
        return await layout.require_confirm_withdraw_balance(ctx)

    if contract.unfreeze_asset_contract:
        return await layout.require_confirm_unfreeze_asset(ctx)

    if contract.update_asset_contract:
        return await layout.require_confirm_update_asset(
            ctx,
            contract.update_asset_contract.description,
            contract.update_asset_contract.url,
        )

    if contract.proposal_create_contract:
        return await layout.require_confirm_proposal_create_contract(
            ctx, contract.proposal_create_contract.parameters
        )

    if contract.proposal_approve_contract:
        return await layout.require_confirm_proposal_approve_contract(
            ctx,
            contract.proposal_approve_contract.proposal_id,
            contract.proposal_approve_contract.is_add_approval,
        )

    if contract.proposal_delete_contract:
        return await layout.require_confirm_proposal_delete_contract(
            ctx, contract.proposal_delete_contract.proposal_id
        )

    if contract.set_account_id:
        return await layout.require_confirm_set_account_id_contract(
            ctx, contract.set_account_id.account_id
        )
    
    if contract.trigger_smart_contract:
        # check if TRC20 transfer/ approval
        data = contract.trigger_smart_contract.data
        action = None

        if data[:16] == b"\xa9\x05\x9c\xbb\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00":
            action = "Transfer"
        elif data[:16] == b"\x09\x5e\xa7\xb3\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00":
            action = "Approve"

        if action:
            token = tokens.token_by_address("TRC20", contract.trigger_smart_contract.contract_address)
            recipient = _address_base58(b"\x41" + data[16:36])
            value = int.from_bytes(data[36:68], "big")
            return await layout.require_confirm_trigger_trc20(
                ctx,
                action,
                token[0],
                token[2] if token[2] else contract.trigger_smart_contract.contract_address,
                value,
                token[3],
                recipient
            )
        raise wire.DataError("Invalid transaction type")

    if contract.exchange_create_contract:
        if not validateToken(
            contract.exchange_create_contract.first_asset_id,
            contract.exchange_create_contract.first_asset_name,
            contract.exchange_create_contract.first_asset_decimals,
            contract.exchange_create_contract.first_asset_signature,
        ):
            raise wire.ProcessError("Token 1 signature not valid")
        if not validateToken(
            contract.exchange_create_contract.second_asset_id,
            contract.exchange_create_contract.second_asset_name,
            contract.exchange_create_contract.second_asset_decimals,
            contract.exchange_create_contract.second_asset_signature,
        ):
            raise wire.ProcessError("Token 2 signature not valid")
        return await layout.require_confirm_exchange_create_contract(
            ctx,
            contract.exchange_create_contract.first_asset_name,
            contract.exchange_create_contract.first_asset_balance,
            contract.exchange_create_contract.first_asset_decimals,
            contract.exchange_create_contract.second_asset_name,
            contract.exchange_create_contract.second_asset_balance,
            contract.exchange_create_contract.second_asset_decimals,
        )

    if contract.exchange_inject_contract:
        if not validateExchange(
            contract.exchange_inject_contract.exchange_id,
            contract.exchange_inject_contract.first_asset_id,
            contract.exchange_inject_contract.first_asset_name,
            contract.exchange_inject_contract.first_asset_decimals,
            contract.exchange_inject_contract.second_asset_id,
            contract.exchange_inject_contract.second_asset_name,
            contract.exchange_inject_contract.second_asset_decimals,
            contract.exchange_inject_contract.exchange_signature,
        ):
            raise wire.ProcessError("Exchange signature not valid")
        return await layout.require_confirm_exchange_inject_contract(
            ctx,
            contract.exchange_inject_contract.exchange_id,
            contract.exchange_inject_contract.first_asset_name
            if contract.exchange_inject_contract.token_id
            == contract.exchange_inject_contract.first_asset_id
            else contract.exchange_inject_contract.second_asset_name,
            contract.exchange_inject_contract.first_asset_decimals
            if contract.exchange_inject_contract.token_id
            == contract.exchange_inject_contract.first_asset_id
            else contract.exchange_inject_contract.second_asset_decimals,
            contract.exchange_inject_contract.quant,
        )

    if contract.exchange_withdraw_contract:
        if not validateExchange(
            contract.exchange_withdraw_contract.exchange_id,
            contract.exchange_withdraw_contract.first_asset_id,
            contract.exchange_withdraw_contract.first_asset_name,
            contract.exchange_withdraw_contract.first_asset_decimals,
            contract.exchange_withdraw_contract.second_asset_id,
            contract.exchange_withdraw_contract.second_asset_name,
            contract.exchange_withdraw_contract.second_asset_decimals,
            contract.exchange_withdraw_contract.exchange_signature,
        ):
            raise wire.ProcessError("Exchange signature not valid")
        return await layout.require_confirm_exchange_withdraw_contract(
            ctx,
            contract.exchange_withdraw_contract.exchange_id,
            contract.exchange_withdraw_contract.first_asset_name
            if contract.exchange_withdraw_contract.token_id
            == contract.exchange_withdraw_contract.first_asset_id
            else contract.exchange_withdraw_contract.second_asset_name,
            contract.exchange_withdraw_contract.first_asset_decimals
            if contract.exchange_withdraw_contract.token_id
            == contract.exchange_withdraw_contract.first_asset_id
            else contract.exchange_withdraw_contract.second_asset_decimals,
            contract.exchange_withdraw_contract.quant,
        )

    if contract.exchange_transaction_contract:
        if not validateExchange(
            contract.exchange_transaction_contract.exchange_id,
            contract.exchange_transaction_contract.first_asset_id,
            contract.exchange_transaction_contract.first_asset_name,
            contract.exchange_transaction_contract.first_asset_decimals,
            contract.exchange_transaction_contract.second_asset_id,
            contract.exchange_transaction_contract.second_asset_name,
            contract.exchange_transaction_contract.second_asset_decimals,
            contract.exchange_transaction_contract.exchange_signature,
        ):
            raise wire.ProcessError("Exchange signature not valid")
        return await layout.require_confirm_exchange_transaction_contract(
            ctx,
            contract.exchange_transaction_contract.exchange_id,
            contract.exchange_transaction_contract.first_asset_name
            if contract.exchange_transaction_contract.token_id
            == contract.exchange_transaction_contract.first_asset_id
            else contract.exchange_transaction_contract.second_asset_name,
            contract.exchange_transaction_contract.first_asset_decimals
            if contract.exchange_transaction_contract.token_id
            == contract.exchange_transaction_contract.first_asset_id
            else contract.exchange_transaction_contract.second_asset_decimals,
            contract.exchange_transaction_contract.second_asset_name
            if contract.exchange_transaction_contract.token_id
            == contract.exchange_transaction_contract.first_asset_id
            else contract.exchange_transaction_contract.first_asset_name,
            contract.exchange_transaction_contract.second_asset_decimals
            if contract.exchange_transaction_contract.token_id
            == contract.exchange_transaction_contract.first_asset_id
            else contract.exchange_transaction_contract.first_asset_decimals,
            contract.exchange_transaction_contract.quant,
            contract.exchange_transaction_contract.expected,
        )

    raise wire.DataError("Invalid transaction type")


def validateToken(id, name, decimals, signature):
    if id == "_":
        id = "TRX"
    MESSAGE = bytes(id + name, "utf-8") + bytes([decimals])
    rs = (int(signature[6]) * 16 + int(signature[7])) * 2
    ss = (int(signature[10 + rs]) * 16 + int(signature[11 + rs])) * 2
    sig = signature[8 : 8 + rs] + signature[12 + rs : 12 + rs + ss]
    return secp256k1.verify(
        unhexlify(TRON_PUBLICKEY), unhexlify(sig), sha256(MESSAGE).digest()
    )


def validateExchange(
    id, token_1, name_1, decimals_1, token_2, name_2, decimals_2, signature
):
    MESSAGE = (
        str(id).encode()
        + bytes(token_1 + name_1, "utf-8")
        + bytes([decimals_1])
        + bytes(token_2 + name_2, "utf-8")
        + bytes([decimals_2])
    )
    rs = (int(signature[6]) * 16 + int(signature[7])) * 2
    ss = (int(signature[10 + rs]) * 16 + int(signature[11 + rs])) * 2
    sig = signature[8 : 8 + rs] + signature[12 + rs : 12 + rs + ss]
    return secp256k1.verify(
        unhexlify(TRON_PUBLICKEY), unhexlify(sig), sha256(MESSAGE).digest()
    )


def validate(msg: TronSignTx):
    if None in (msg.contract,):
        raise wire.ProcessError("Some of the required fields are missing (contract)")
