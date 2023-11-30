from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from consts import StellarMessageType
    from trezor.utils import Writer


async def process_operation(w: Writer, op: StellarMessageType) -> None:
    # Importing the stuff inside (only) function saves around 100 bytes here
    # (probably because the local lookup is more efficient than a global lookup)

    # Saves about 75 bytes here, to have just one import instead of 13
    import trezor.messages as messages

    from .. import consts, writers
    from . import layout, serialize

    if op.source_account:
        await layout.confirm_source_account(op.source_account)
    serialize.write_account(w, op.source_account)
    writers.write_uint32(w, consts.get_op_code(op))
    # NOTE: each branch below has 45 bytes (26 the actions, 19 the condition)
    if messages.StellarAccountMergeOp.is_type_of(op):
        await layout.confirm_account_merge_op(op)
        serialize.write_account_merge_op(w, op)
    elif messages.StellarAllowTrustOp.is_type_of(op):
        await layout.confirm_allow_trust_op(op)
        serialize.write_allow_trust_op(w, op)
    elif messages.StellarBumpSequenceOp.is_type_of(op):
        await layout.confirm_bump_sequence_op(op)
        serialize.write_bump_sequence_op(w, op)
    elif messages.StellarChangeTrustOp.is_type_of(op):
        await layout.confirm_change_trust_op(op)
        serialize.write_change_trust_op(w, op)
    elif messages.StellarCreateAccountOp.is_type_of(op):
        await layout.confirm_create_account_op(op)
        serialize.write_create_account_op(w, op)
    elif messages.StellarCreatePassiveSellOfferOp.is_type_of(op):
        await layout.confirm_create_passive_sell_offer_op(op)
        serialize.write_create_passive_sell_offer_op(w, op)
    elif messages.StellarManageDataOp.is_type_of(op):
        await layout.confirm_manage_data_op(op)
        serialize.write_manage_data_op(w, op)
    elif messages.StellarManageBuyOfferOp.is_type_of(op):
        await layout.confirm_manage_buy_offer_op(op)
        serialize.write_manage_buy_offer_op(w, op)
    elif messages.StellarManageSellOfferOp.is_type_of(op):
        await layout.confirm_manage_sell_offer_op(op)
        serialize.write_manage_sell_offer_op(w, op)
    elif messages.StellarPathPaymentStrictReceiveOp.is_type_of(op):
        await layout.confirm_path_payment_strict_receive_op(op)
        serialize.write_path_payment_strict_receive_op(w, op)
    elif messages.StellarPathPaymentStrictSendOp.is_type_of(op):
        await layout.confirm_path_payment_strict_send_op(op)
        serialize.write_path_payment_strict_send_op(w, op)
    elif messages.StellarPaymentOp.is_type_of(op):
        await layout.confirm_payment_op(op)
        serialize.write_payment_op(w, op)
    elif messages.StellarSetOptionsOp.is_type_of(op):
        await layout.confirm_set_options_op(op)
        serialize.write_set_options_op(w, op)
    elif messages.StellarClaimClaimableBalanceOp.is_type_of(op):
        await layout.confirm_claim_claimable_balance_op(op)
        serialize.write_claim_claimable_balance_op(w, op)
    else:
        raise ValueError("Unknown operation")
