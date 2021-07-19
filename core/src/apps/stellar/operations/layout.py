from trezor.messages import (
    StellarAccountMergeOp,
    StellarAllowTrustOp,
    StellarAssetType,
    StellarBumpSequenceOp,
    StellarChangeTrustOp,
    StellarCreateAccountOp,
    StellarCreatePassiveOfferOp,
    StellarManageDataOp,
    StellarManageOfferOp,
    StellarPathPaymentOp,
    StellarPaymentOp,
    StellarSetOptionsOp,
)
from trezor.ui.layouts import (
    confirm_address,
    confirm_amount,
    confirm_blob,
    confirm_metadata,
    confirm_output,
    confirm_properties,
    confirm_text,
)
from trezor.wire import ProcessError

from .. import consts, helpers
from ..layout import format_amount, format_asset


async def confirm_source_account(ctx, source_account: str):
    await confirm_address(
        ctx,
        "Confirm operation",
        source_account,
        description="Source account:",
        br_type="op_source_account",
    )


async def confirm_allow_trust_op(ctx, op: StellarAllowTrustOp):
    await confirm_properties(
        ctx,
        "op_allow_trust",
        title="Allow trust" if op.is_authorized else "Revoke trust",
        props=(
            ("Asset", op.asset_code),
            ("Trusted Account", op.trusted_account),
        ),
    )


async def confirm_account_merge_op(ctx, op: StellarAccountMergeOp):
    await confirm_address(
        ctx,
        "Account Merge",
        op.destination_account,
        description="All XLM will be sent to:",
        br_type="op_account_merge",
    )


async def confirm_bump_sequence_op(ctx, op: StellarBumpSequenceOp):
    await confirm_metadata(
        ctx,
        "op_bump",
        "Bump Sequence",
        content="Set sequence to {}?",
        param=str(op.bump_to),
    )


async def confirm_change_trust_op(ctx, op: StellarChangeTrustOp):
    await confirm_amount(
        ctx,
        title="Delete trust" if op.limit == 0 else "Add trust",
        amount=format_amount(op.limit, op.asset),
        description="Limit:",
        br_type="op_change_trust",
    )
    await confirm_asset_issuer(ctx, op.asset)


async def confirm_create_account_op(ctx, op: StellarCreateAccountOp):
    await confirm_properties(
        ctx,
        "op_create_account",
        "Create Account",
        props=(
            ("Account", op.new_account),
            ("Initial Balance", format_amount(op.starting_balance)),
        ),
    )


async def confirm_create_passive_offer_op(ctx, op: StellarCreatePassiveOfferOp):
    if op.amount == 0:
        text = "Delete Passive Offer"
    else:
        text = "New Passive Offer"
    await _confirm_offer(ctx, text, op)


async def confirm_manage_offer_op(ctx, op: StellarManageOfferOp):
    if op.offer_id == 0:
        text = "New Offer"
    else:
        if op.amount == 0:
            text = "Delete"
        else:
            text = "Update"
        text += " #%d" % op.offer_id
    await _confirm_offer(ctx, text, op)


async def _confirm_offer(ctx, title, op):
    await confirm_properties(
        ctx,
        "op_offer",
        title=title,
        props=(
            ("Selling:", format_amount(op.amount, op.selling_asset)),
            ("Buying:", format_asset(op.buying_asset)),
            (
                "Price per {}:".format(format_asset(op.buying_asset)),
                str(op.price_n / op.price_d),
            ),
        ),
    )
    await confirm_asset_issuer(ctx, op.selling_asset)
    await confirm_asset_issuer(ctx, op.buying_asset)


async def confirm_manage_data_op(ctx, op: StellarManageDataOp):
    from trezor.crypto.hashlib import sha256

    if op.value:
        digest = sha256(op.value).digest()
        await confirm_properties(
            ctx,
            "op_data",
            "Set data",
            props=(("Key:", op.key), ("Value (SHA-256):", digest)),
        )
    else:
        await confirm_metadata(
            ctx,
            "op_data",
            "Clear data",
            "Do you want to clear value key {}?",
            param=op.key,
        )


async def confirm_path_payment_op(ctx, op: StellarPathPaymentOp):
    await confirm_output(
        ctx,
        address=op.destination_account,
        amount=format_amount(op.destination_amount, op.destination_asset),
        title="Path Pay",
    )
    await confirm_asset_issuer(ctx, op.destination_asset)
    # confirm what the sender is using to pay
    await confirm_amount(
        ctx,
        title="Debited amount",
        amount=format_amount(op.send_max, op.send_asset),
        description="Pay at most:",
        br_type="op_path_payment",
    )
    await confirm_asset_issuer(ctx, op.send_asset)


async def confirm_payment_op(ctx, op: StellarPaymentOp):
    await confirm_output(
        ctx,
        address=op.destination_account,
        amount=format_amount(op.amount, op.asset),
    )
    await confirm_asset_issuer(ctx, op.asset)


async def confirm_set_options_op(ctx, op: StellarSetOptionsOp):
    if op.inflation_destination_account:
        await confirm_address(
            ctx,
            "Inflation",
            op.inflation_destination_account,
            description="Destination:",
            br_type="op_inflation",
        )

    if op.clear_flags:
        t = _format_flags(op.clear_flags)
        await confirm_text(ctx, "op_set_options", "Clear flags", data=t)

    if op.set_flags:
        t = _format_flags(op.set_flags)
        await confirm_text(ctx, "op_set_options", "Set flags", data=t)

    thresholds = _format_thresholds(op)
    if thresholds:
        await confirm_properties(
            ctx, "op_thresholds", "Account Thresholds", props=thresholds
        )

    if op.home_domain:
        await confirm_text(ctx, "op_home_domain", "Home Domain", op.home_domain)

    if op.signer_type is not None:
        if op.signer_weight > 0:
            title = "Add Signer"
        else:
            title = "Remove Signer"
        data: str | bytes = ""
        if op.signer_type == consts.SIGN_TYPE_ACCOUNT:
            description = "Account:"
            data = helpers.address_from_public_key(op.signer_key)
        elif op.signer_type == consts.SIGN_TYPE_PRE_AUTH:
            description = "Pre-auth transaction:"
            data = op.signer_key
        elif op.signer_type == consts.SIGN_TYPE_HASH:
            description = "Hash:"
            data = op.signer_key
        else:
            raise ProcessError("Stellar: invalid signer type")

        await confirm_blob(
            ctx,
            "op_signer",
            title=title,
            description=description,
            data=data,
        )


def _format_thresholds(op: StellarSetOptionsOp) -> list[(str, str)]:
    props = []
    if op.master_weight is not None:
        props.append(("Master Weight:", str(op.master_weight)))
    if op.low_threshold is not None:
        props.append(("Low:", str(op.low_threshold)))
    if op.medium_threshold is not None:
        props.append(("Medium:", str(op.medium_threshold)))
    if op.high_threshold is not None:
        props.append(("High:", str(op.high_threshold)))
    return props


def _format_flags(flags: int) -> tuple:
    if flags > consts.FLAGS_MAX_SIZE:
        raise ProcessError("Stellar: invalid flags")
    text = "{}{}{}".format(
        "AUTH_REQUIRED\n" if flags & consts.FLAG_AUTH_REQUIRED else "",
        "AUTH_REVOCABLE\n" if flags & consts.FLAG_AUTH_REVOCABLE else "",
        "AUTH_IMMUTABLE\n" if flags & consts.FLAG_AUTH_IMMUTABLE else "",
    )
    return text


async def confirm_asset_issuer(ctx, asset: StellarAssetType):
    if asset is None or asset.type == consts.ASSET_TYPE_NATIVE:
        return
    await confirm_address(
        ctx,
        "Confirm Issuer",
        asset.issuer,
        description="{} issuer:".format(asset.code),
        br_type="confirm_asset_issuer",
    )
