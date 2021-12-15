from trezor.enums import StellarAssetType, StellarSignerType
from trezor.messages import (
    StellarAccountMergeOp,
    StellarAllowTrustOp,
    StellarAsset,
    StellarBumpSequenceOp,
    StellarChangeTrustOp,
    StellarCreateAccountOp,
    StellarCreatePassiveSellOfferOp,
    StellarManageBuyOfferOp,
    StellarManageDataOp,
    StellarManageSellOfferOp,
    StellarPathPaymentStrictReceiveOp,
    StellarPathPaymentStrictSendOp,
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
from trezor.wire import DataError, ProcessError

from .. import consts, helpers
from ..layout import format_amount, format_asset

if False:
    from trezor.wire import Context


async def confirm_source_account(ctx: Context, source_account: str) -> None:
    await confirm_address(
        ctx,
        "Confirm operation",
        source_account,
        description="Source account:",
        br_type="op_source_account",
    )


async def confirm_allow_trust_op(ctx: Context, op: StellarAllowTrustOp) -> None:
    await confirm_properties(
        ctx,
        "op_allow_trust",
        title="Allow trust" if op.is_authorized else "Revoke trust",
        props=(
            ("Asset", op.asset_code),
            ("Trusted Account", op.trusted_account),
        ),
    )


async def confirm_account_merge_op(ctx: Context, op: StellarAccountMergeOp) -> None:
    await confirm_address(
        ctx,
        "Account Merge",
        op.destination_account,
        description="All XLM will be sent to:",
        br_type="op_account_merge",
    )


async def confirm_bump_sequence_op(ctx: Context, op: StellarBumpSequenceOp) -> None:
    await confirm_metadata(
        ctx,
        "op_bump",
        "Bump Sequence",
        content="Set sequence to {}?",
        param=str(op.bump_to),
    )


async def confirm_change_trust_op(ctx: Context, op: StellarChangeTrustOp) -> None:
    await confirm_amount(
        ctx,
        title="Delete trust" if op.limit == 0 else "Add trust",
        amount=format_amount(op.limit, op.asset),
        description="Limit:",
        br_type="op_change_trust",
    )
    await confirm_asset_issuer(ctx, op.asset)


async def confirm_create_account_op(ctx: Context, op: StellarCreateAccountOp) -> None:
    await confirm_properties(
        ctx,
        "op_create_account",
        "Create Account",
        props=(
            ("Account", op.new_account),
            ("Initial Balance", format_amount(op.starting_balance)),
        ),
    )


async def confirm_create_passive_sell_offer_op(
    ctx: Context, op: StellarCreatePassiveSellOfferOp
) -> None:
    if op.amount == 0:
        text = "Delete Passive Offer"
    else:
        text = "New Passive Offer"
    await _confirm_offer(ctx, text, op)


async def confirm_manage_buy_offer_op(
    ctx: Context, op: StellarManageBuyOfferOp
) -> None:
    await _confirm_manage_offer_op_common(ctx, op)


async def confirm_manage_sell_offer_op(
    ctx: Context, op: StellarManageSellOfferOp
) -> None:
    await _confirm_manage_offer_op_common(ctx, op)


async def _confirm_manage_offer_op_common(
    ctx: Context, op: StellarManageBuyOfferOp | StellarManageSellOfferOp
) -> None:
    if op.offer_id == 0:
        text = "New Offer"
    else:
        if op.amount == 0:
            text = "Delete"
        else:
            text = "Update"
        text += f" #{op.offer_id}"
    await _confirm_offer(ctx, text, op)


async def _confirm_offer(
    ctx: Context,
    title: str,
    op: StellarCreatePassiveSellOfferOp
    | StellarManageSellOfferOp
    | StellarManageBuyOfferOp,
) -> None:
    if StellarManageBuyOfferOp.is_type_of(op):
        buying = ("Buying:", format_amount(op.amount, op.buying_asset))
        selling = ("Selling:", format_asset(op.selling_asset))
        price = (
            f"Price per {format_asset(op.selling_asset)}:",
            str(op.price_n / op.price_d),
        )
        await confirm_properties(
            ctx,
            "op_offer",
            title=title,
            props=(buying, selling, price),
        )
    else:
        selling = ("Selling:", format_amount(op.amount, op.selling_asset))
        buying = ("Buying:", format_asset(op.buying_asset))
        price = (
            f"Price per {format_asset(op.buying_asset)}:",
            str(op.price_n / op.price_d),
        )
        await confirm_properties(
            ctx,
            "op_offer",
            title=title,
            props=(selling, buying, price),
        )

    await confirm_asset_issuer(ctx, op.selling_asset)
    await confirm_asset_issuer(ctx, op.buying_asset)


async def confirm_manage_data_op(ctx: Context, op: StellarManageDataOp) -> None:
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


async def confirm_path_payment_strict_receive_op(
    ctx: Context, op: StellarPathPaymentStrictReceiveOp
) -> None:
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
        br_type="op_path_payment_strict_receive",
    )
    await confirm_asset_issuer(ctx, op.send_asset)


async def confirm_path_payment_strict_send_op(
    ctx: Context, op: StellarPathPaymentStrictSendOp
) -> None:
    await confirm_output(
        ctx,
        address=op.destination_account,
        amount=format_amount(op.destination_min, op.destination_asset),
        title="Path Pay at least",
    )
    await confirm_asset_issuer(ctx, op.destination_asset)
    # confirm what the sender is using to pay
    await confirm_amount(
        ctx,
        title="Debited amount",
        amount=format_amount(op.send_amount, op.send_asset),
        description="Pay:",
        br_type="op_path_payment_strict_send",
    )
    await confirm_asset_issuer(ctx, op.send_asset)


async def confirm_payment_op(ctx: Context, op: StellarPaymentOp) -> None:
    await confirm_output(
        ctx,
        address=op.destination_account,
        amount=format_amount(op.amount, op.asset),
    )
    await confirm_asset_issuer(ctx, op.asset)


async def confirm_set_options_op(ctx: Context, op: StellarSetOptionsOp) -> None:
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
        if op.signer_key is None or op.signer_weight is None:
            raise DataError("Stellar: invalid signer option data.")

        if op.signer_weight > 0:
            title = "Add Signer"
        else:
            title = "Remove Signer"
        data: str | bytes = ""
        if op.signer_type == StellarSignerType.ACCOUNT:
            description = "Account:"
            data = helpers.address_from_public_key(op.signer_key)
        elif op.signer_type == StellarSignerType.PRE_AUTH:
            description = "Pre-auth transaction:"
            data = op.signer_key
        elif op.signer_type == StellarSignerType.HASH:
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


def _format_thresholds(op: StellarSetOptionsOp) -> list[tuple[str, str]]:
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


def _format_flags(flags: int) -> str:
    if flags > consts.FLAGS_MAX_SIZE:
        raise ProcessError("Stellar: invalid flags")
    flags_set = []
    if flags & consts.FLAG_AUTH_REQUIRED:
        flags_set.append("AUTH_REQUIRED\n")
    if flags & consts.FLAG_AUTH_REVOCABLE:
        flags_set.append("AUTH_REVOCABLE\n")
    if flags & consts.FLAG_AUTH_IMMUTABLE:
        flags_set.append("AUTH_IMMUTABLE\n")
    return "".join(flags_set)


async def confirm_asset_issuer(ctx: Context, asset: StellarAsset) -> None:
    if asset.type == StellarAssetType.NATIVE:
        return
    if asset.issuer is None or asset.code is None:
        raise DataError("Stellar: invalid asset definition")
    await confirm_address(
        ctx,
        "Confirm Issuer",
        asset.issuer,
        description=f"{asset.code} issuer:",
        br_type="confirm_asset_issuer",
    )
