from ubinascii import unhexlify

from trezor import wire
from trezor.crypto.curve import secp256k1
from trezor.crypto.hashlib import sha256
from trezor.messages.TronSignedTx import TronSignedTx
from trezor.messages.TronSignTx import TronSignTx

from apps.common import paths
from apps.tron import CURVE, TRON_PUBLICKEY, layout
from apps.tron.address import get_address_from_public_key, validate_full_path
from apps.tron.serialize import serialize


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
            raise wire.ProcessError(
                "Some of the required fields are missing (contract)"
            )
        return await layout.require_confirm_tx_asset(
            ctx,
            contract.transfer_asset_contract.asset_name,
            contract.transfer_asset_contract.to_address,
            contract.transfer_asset_contract.amount,
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
        return await layout.require_confirm_asset_issue(
            ctx,
            contract.asset_issue_contract.name,
            contract.asset_issue_contract.abbr,
            contract.asset_issue_contract.total_supply,
            contract.asset_issue_contract.trx_num,
            contract.asset_issue_contract.num,
        )

    if contract.witness_update_contract:
        return await layout.require_confirm_witness_update(
            ctx,
            str(owner_address, "utf-8"),
            contract.witness_update_contract.update_url,
        )

    if contract.participate_asset_issue_contract:
        return await layout.require_confirm_participate_asset(
            ctx,
            contract.participate_asset_issue_contract.asset_name,
            contract.participate_asset_issue_contract.amount,
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
        )

    if contract.unfreeze_balance_contract:
        return await layout.require_confirm_unfreeze_balance(ctx)

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

    if contract.create_smart_contract:
        return await layout.require_confirm_create_smart_contract(
            ctx, contract.create_smart_contract
        )

    if contract.trigger_smart_contract:
        return await layout.require_confirm_trigger_smart_contract(
            ctx,
            contract.trigger_smart_contract.contract_address,
            contract.trigger_smart_contract,
        )

    if contract.update_setting_contract:
        return await layout.require_confirm_update_setting_contract(
            ctx,
            contract.update_setting_contract.contract_address,
            contract.update_setting_contract.consume_user_resource_percent,
        )

    if contract.exchange_create_contract:
        return await layout.require_confirm_exchange_create_contract(
            ctx,
            contract.exchange_create_contract.first_token_id,
            contract.exchange_create_contract.first_token_balance,
            contract.exchange_create_contract.second_token_id,
            contract.exchange_create_contract.second_token_balance,
        )

    if contract.exchange_inject_contract:
        return await layout.require_confirm_exchange_inject_contract(
            ctx,
            contract.exchange_inject_contract.exchange_id,
            contract.exchange_inject_contract.token_id,
            contract.exchange_inject_contract.quant,
        )

    if contract.exchange_withdraw_contract:
        return await layout.require_confirm_exchange_withdraw_contract(
            ctx,
            contract.exchange_withdraw_contract.exchange_id,
            contract.exchange_withdraw_contract.token_id,
            contract.exchange_withdraw_contract.quant,
        )

    if contract.exchange_transaction_contract:
        return await layout.require_confirm_exchange_transaction_contract(
            ctx,
            contract.exchange_withdraw_contract.exchange_id,
            contract.exchange_withdraw_contract.token_id,
            contract.exchange_withdraw_contract.quant,
            contract.exchange_withdraw_contract.expected,
        )

    if contract.update_energy_limit_contract:
        return await layout.require_confirm_update_energy_limit_contract(
            ctx,
            contract.update_energy_limit_contract.contract_address,
            contract.update_energy_limit_contract.origin_energy_limit,
        )

    if contract.account_permission_update_contract:
        return await layout.require_confirm_account_permission_update_contract(ctx)

    if contract.cancel_deferred_transaction_contract:
        return await layout.require_confirm_cancel_deferred_transaction_contract(ctx)

    raise wire.DataError("Invalid transaction type")


def validateToken(id, name, decimals, signature):
    MESSAGE = bytes(id + name, "utf-8") + bytes([decimals])
    return secp256k1.verify(
        unhexlify(TRON_PUBLICKEY), unhexlify(signature), sha256(MESSAGE).digest()
    )


def validate(msg: TronSignTx):
    if None in (msg.contract,):
        raise wire.ProcessError("Some of the required fields are missing (contract)")
