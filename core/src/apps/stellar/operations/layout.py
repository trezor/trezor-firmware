from ubinascii import hexlify

from trezor.enums import ButtonRequestType
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
from trezor.ui.layouts import confirm_metadata
from trezor.wire import ProcessError

from .. import consts, helpers
from ..layout import format_amount, require_confirm_op, ui


async def confirm_source_account(ctx, source_account: str):
    await require_confirm_op(ctx, "confirm_source", "Source account:", source_account)


async def confirm_allow_trust_op(ctx, op: StellarAllowTrustOp):
    await require_confirm_op(
        ctx,
        "op_allow_trust",
        subtitle="Allow Trust" if op.is_authorized else "Revoke Trust",
        description="of %s by:" % op.asset_code,
        data=op.trusted_account,
        is_account=True,
    )


async def confirm_account_merge_op(ctx, op: StellarAccountMergeOp):
    await require_confirm_op(
        ctx,
        "op_merge",
        "Account Merge",
        description="All XLM will be sent to:",
        data=op.destination_account,
        is_account=True,
    )


async def confirm_bump_sequence_op(ctx, op: StellarBumpSequenceOp):
    await require_confirm_op(
        ctx,
        "op_bump",
        "Bump Sequence",
        description="Set sequence to",
        data=str(op.bump_to),
        split=False,
    )


async def confirm_change_trust_op(ctx, op: StellarChangeTrustOp):
    await require_confirm_op(
        ctx,
        "op_change_trust",
        subtitle="Delete Trust" if op.limit == 0 else "Add Trust",
        description="Asset: %s\nAmount: %s"
        % (op.asset.code, format_amount(op.limit, ticker=False)),
        data="",
        split=False,
    )
    await confirm_asset_issuer(ctx, op.asset)


async def confirm_create_account_op(ctx, op: StellarCreateAccountOp):
    await require_confirm_op(
        ctx,
        "op_account",
        subtitle="Create Account",
        description="with %s" % format_amount(op.starting_balance),
        data=op.new_account,
        is_account=True,
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
    await require_confirm_op(
        ctx,
        "op_offer",
        subtitle=title,
        description="Sell %s %s\nFor %f\nPer %s"
        % (
            format_amount(op.amount, ticker=False),
            op.selling_asset.code,
            op.price_n / op.price_d,
            format_asset_code(op.buying_asset),
        ),
        data="",
        split=False,
    )
    await confirm_asset_issuer(ctx, op.selling_asset)
    await confirm_asset_issuer(ctx, op.buying_asset)


async def confirm_manage_data_op(ctx, op: StellarManageDataOp):
    from trezor.crypto.hashlib import sha256

    if op.value:
        title = "Set"
    else:
        title = "Clear"
    await require_confirm_op(ctx, "op_data", "%s data value key" % title, op.key)

    if op.value:
        digest = sha256(op.value).digest()
        digest_str = hexlify(digest).decode()
        await require_confirm_op(ctx, "op_data_value", "Value (SHA-256):", digest_str)


async def confirm_path_payment_op(ctx, op: StellarPathPaymentOp):
    await require_confirm_op(
        ctx,
        "op_path_payment",
        subtitle="Path Pay %s\n%s to:"
        % (
            format_amount(op.destination_amount, ticker=False),
            format_asset_code(op.destination_asset),
        ),
        data=op.destination_account,
        is_account=True,
    )
    await confirm_asset_issuer(ctx, op.destination_asset)
    # confirm what the sender is using to pay
    await confirm_metadata(
        ctx,
        "op_path_payment",
        "Confirm operation",
        content="Pay using\n{}\nThis amount is debited from your account.",
        param="{}\n{}".format(
            format_amount(op.send_max, ticker=False),
            format_asset_code(op.send_asset),
        ),
        icon=ui.ICON_CONFIRM,
        hide_continue=True,
        br_code=ButtonRequestType.ConfirmOutput,
    )
    await confirm_asset_issuer(ctx, op.send_asset)


async def confirm_payment_op(ctx, op: StellarPaymentOp):
    description = "Pay {}\n{} to:".format(
        format_amount(op.amount, ticker=False), format_asset_code(op.asset)
    )
    await require_confirm_op(
        ctx, "op_payment", description, op.destination_account, is_account=True
    )

    await confirm_asset_issuer(ctx, op.asset)


async def confirm_set_options_op(ctx, op: StellarSetOptionsOp):
    if op.inflation_destination_account:
        await require_confirm_op(
            ctx,
            "op_inflation",
            "Set Inflation Destination",
            op.inflation_destination_account,
        )
    if op.clear_flags:
        t = _format_flags(op.clear_flags)
        await require_confirm_op(ctx, "op_clear_flags", "Clear Flags", t, split=False)
    if op.set_flags:
        t = _format_flags(op.set_flags)
        await require_confirm_op(ctx, "op_set_flags", "Set Flags", t, split=False)
    thresholds = _format_thresholds(op)
    if thresholds:
        await require_confirm_op(
            ctx,
            "op_thresholds",
            "Account Thresholds",
            thresholds,
            split=False,
        )
    if op.home_domain:
        await require_confirm_op(ctx, "op_home_domain", "Home Domain", op.home_domain)
    if op.signer_type is not None:
        if op.signer_weight > 0:
            t = "Add Signer (%s)"
        else:
            t = "Remove Signer (%s)"
        if op.signer_type == consts.SIGN_TYPE_ACCOUNT:
            await require_confirm_op(
                ctx,
                "op_signer",
                t % "acc",
                helpers.address_from_public_key(op.signer_key),
            )
        elif op.signer_type in (consts.SIGN_TYPE_PRE_AUTH, consts.SIGN_TYPE_HASH):
            if op.signer_type == consts.SIGN_TYPE_PRE_AUTH:
                signer_type = "auth"
            else:
                signer_type = "hash"
            await require_confirm_op(
                ctx,
                "op_signer",
                t % signer_type,
                hexlify(op.signer_key).decode(),
            )
        else:
            raise ProcessError("Stellar: invalid signer type")


def _format_thresholds(op: StellarSetOptionsOp) -> tuple:
    text = ""
    if op.master_weight is not None:
        text += "Master Weight: %d\n" % op.master_weight
    if op.low_threshold is not None:
        text += "Low: %d\n" % op.low_threshold
    if op.medium_threshold is not None:
        text += "Medium: %d\n" % op.medium_threshold
    if op.high_threshold is not None:
        text += "High: %d\n" % op.high_threshold
    return text


def _format_flags(flags: int) -> tuple:
    if flags > consts.FLAGS_MAX_SIZE:
        raise ProcessError("Stellar: invalid flags")
    text = "{}{}{}".format(
        "AUTH_REQUIRED\n" if flags & consts.FLAG_AUTH_REQUIRED else "",
        "AUTH_REVOCABLE\n" if flags & consts.FLAG_AUTH_REVOCABLE else "",
        "AUTH_IMMUTABLE\n" if flags & consts.FLAG_AUTH_IMMUTABLE else "",
    )
    return text


def format_asset_code(asset: StellarAssetType) -> str:
    if asset is None or asset.type == consts.ASSET_TYPE_NATIVE:
        return "XLM (native)"
    return asset.code


async def confirm_asset_issuer(ctx, asset: StellarAssetType):
    if asset is None or asset.type == consts.ASSET_TYPE_NATIVE:
        return
    await require_confirm_op(
        ctx,
        "confirm_issuer",
        title="Confirm issuer",
        subtitle="%s issuer:" % asset.code,
        data=asset.issuer,
    )
