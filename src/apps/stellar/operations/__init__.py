from apps.stellar.operations.serialize import *
from apps.stellar.operations.layout import *


async def operation(ctx, w, op):
    if op.source_account:
        await confirm_source_account(ctx, op.source_account)
    serialize_account(w, op.source_account)
    write_uint32(w, get_op_code(op))
    if isinstance(op, StellarAccountMergeOp):
        await confirm_account_merge_op(ctx, op)
        serialize_account_merge_op(w, op)
    elif isinstance(op, StellarAllowTrustOp):
        await confirm_allow_trust_op(ctx, op)
        serialize_allow_trust_op(w, op)
    elif isinstance(op, StellarBumpSequenceOp):
        await confirm_bump_sequence_op(ctx, op)
        serialize_bump_sequence_op(w, op)
    elif isinstance(op, StellarChangeTrustOp):
        await confirm_change_trust_op(ctx, op)
        serialize_change_trust_op(w, op)
    elif isinstance(op, StellarCreateAccountOp):
        await confirm_create_account_op(ctx, op)
        serialize_create_account_op(w, op)
    elif isinstance(op, StellarCreatePassiveOfferOp):
        await confirm_create_passive_offer_op(ctx, op)
        serialize_create_passive_offer_op(w, op)
    elif isinstance(op, StellarManageDataOp):
        await confirm_manage_data_op(ctx, op)
        serialize_manage_data_op(w, op)
    elif isinstance(op, StellarManageOfferOp):
        await confirm_manage_offer_op(ctx, op)
        serialize_manage_offer_op(w, op)
    elif isinstance(op, StellarPathPaymentOp):
        await confirm_path_payment_op(ctx, op)
        serialize_path_payment_op(w, op)
    elif isinstance(op, StellarPaymentOp):
        await confirm_payment_op(ctx, op)
        serialize_payment_op(w, op)
    elif isinstance(op, StellarSetOptionsOp):
        await confirm_set_options_op(ctx, op)
        serialize_set_options_op(w, op)
    else:
        raise ValueError('Stellar: unknown operation')
