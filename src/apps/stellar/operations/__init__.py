from apps.stellar import consts, writers
from apps.stellar.operations import layout, serialize


async def operation(ctx, w, op):
    if op.source_account:
        await layout.confirm_source_account(ctx, op.source_account)
    serialize.serialize_account(w, op.source_account)
    writers.write_uint32(w, consts.get_op_code(op))
    if isinstance(op, serialize.StellarAccountMergeOp):
        await layout.confirm_account_merge_op(ctx, op)
        serialize.serialize_account_merge_op(w, op)
    elif isinstance(op, serialize.StellarAllowTrustOp):
        await layout.confirm_allow_trust_op(ctx, op)
        serialize.serialize_allow_trust_op(w, op)
    elif isinstance(op, serialize.StellarBumpSequenceOp):
        await layout.confirm_bump_sequence_op(ctx, op)
        serialize.serialize_bump_sequence_op(w, op)
    elif isinstance(op, serialize.StellarChangeTrustOp):
        await layout.confirm_change_trust_op(ctx, op)
        serialize.serialize_change_trust_op(w, op)
    elif isinstance(op, serialize.StellarCreateAccountOp):
        await layout.confirm_create_account_op(ctx, op)
        serialize.serialize_create_account_op(w, op)
    elif isinstance(op, serialize.StellarCreatePassiveOfferOp):
        await layout.confirm_create_passive_offer_op(ctx, op)
        serialize.serialize_create_passive_offer_op(w, op)
    elif isinstance(op, serialize.StellarManageDataOp):
        await layout.confirm_manage_data_op(ctx, op)
        serialize.serialize_manage_data_op(w, op)
    elif isinstance(op, serialize.StellarManageOfferOp):
        await layout.confirm_manage_offer_op(ctx, op)
        serialize.serialize_manage_offer_op(w, op)
    elif isinstance(op, serialize.StellarPathPaymentOp):
        await layout.confirm_path_payment_op(ctx, op)
        serialize.serialize_path_payment_op(w, op)
    elif isinstance(op, serialize.StellarPaymentOp):
        await layout.confirm_payment_op(ctx, op)
        serialize.serialize_payment_op(w, op)
    elif isinstance(op, serialize.StellarSetOptionsOp):
        await layout.confirm_set_options_op(ctx, op)
        serialize.serialize_set_options_op(w, op)
    else:
        raise ValueError("serialize.Stellar: unknown operation")
