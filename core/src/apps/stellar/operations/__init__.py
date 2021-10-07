from .. import consts, writers
from . import layout, serialize

if False:
    from trezor.utils import Writer
    from trezor.wire import Context


async def process_operation(
    ctx: Context, w: Writer, op: consts.StellarMessageType
) -> None:
    if op.source_account:
        await layout.confirm_source_account(ctx, op.source_account)
    serialize.write_account(w, op.source_account)
    writers.write_uint32(w, consts.get_op_code(op))
    if serialize.StellarAccountMergeOp.is_type_of(op):
        await layout.confirm_account_merge_op(ctx, op)
        serialize.write_account_merge_op(w, op)
    elif serialize.StellarAllowTrustOp.is_type_of(op):
        await layout.confirm_allow_trust_op(ctx, op)
        serialize.write_allow_trust_op(w, op)
    elif serialize.StellarBumpSequenceOp.is_type_of(op):
        await layout.confirm_bump_sequence_op(ctx, op)
        serialize.write_bump_sequence_op(w, op)
    elif serialize.StellarChangeTrustOp.is_type_of(op):
        await layout.confirm_change_trust_op(ctx, op)
        serialize.write_change_trust_op(w, op)
    elif serialize.StellarCreateAccountOp.is_type_of(op):
        await layout.confirm_create_account_op(ctx, op)
        serialize.write_create_account_op(w, op)
    elif serialize.StellarCreatePassiveSellOfferOp.is_type_of(op):
        await layout.confirm_create_passive_sell_offer_op(ctx, op)
        serialize.write_create_passive_sell_offer_op(w, op)
    elif serialize.StellarManageDataOp.is_type_of(op):
        await layout.confirm_manage_data_op(ctx, op)
        serialize.write_manage_data_op(w, op)
    elif serialize.StellarManageBuyOfferOp.is_type_of(op):
        await layout.confirm_manage_buy_offer_op(ctx, op)
        serialize.write_manage_buy_offer_op(w, op)
    elif serialize.StellarManageSellOfferOp.is_type_of(op):
        await layout.confirm_manage_sell_offer_op(ctx, op)
        serialize.write_manage_sell_offer_op(w, op)
    elif serialize.StellarPathPaymentStrictReceiveOp.is_type_of(op):
        await layout.confirm_path_payment_strict_receive_op(ctx, op)
        serialize.write_path_payment_strict_receive_op(w, op)
    elif serialize.StellarPathPaymentStrictSendOp.is_type_of(op):
        await layout.confirm_path_payment_strict_send_op(ctx, op)
        serialize.write_path_payment_strict_send_op(w, op)
    elif serialize.StellarPaymentOp.is_type_of(op):
        await layout.confirm_payment_op(ctx, op)
        serialize.write_payment_op(w, op)
    elif serialize.StellarSetOptionsOp.is_type_of(op):
        await layout.confirm_set_options_op(ctx, op)
        serialize.write_set_options_op(w, op)
    else:
        raise ValueError("Unknown operation")
