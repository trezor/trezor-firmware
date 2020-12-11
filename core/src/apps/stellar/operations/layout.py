from ubinascii import hexlify

from trezor.messages import ButtonRequestType
from trezor.messages.StellarAccountMergeOp import StellarAccountMergeOp
from trezor.messages.StellarAllowTrustOp import StellarAllowTrustOp
from trezor.messages.StellarAssetType import StellarAssetType
from trezor.messages.StellarBumpSequenceOp import StellarBumpSequenceOp
from trezor.messages.StellarChangeTrustOp import StellarChangeTrustOp
from trezor.messages.StellarCreateAccountOp import StellarCreateAccountOp
from trezor.messages.StellarCreatePassiveOfferOp import StellarCreatePassiveOfferOp
from trezor.messages.StellarManageDataOp import StellarManageDataOp
from trezor.messages.StellarManageOfferOp import StellarManageOfferOp
from trezor.messages.StellarPathPaymentOp import StellarPathPaymentOp
from trezor.messages.StellarPaymentOp import StellarPaymentOp
from trezor.messages.StellarSetOptionsOp import StellarSetOptionsOp
from trezor.ui.components.tt.text import Text
from trezor.wire import ProcessError

from .. import consts, helpers
from ..layout import format_amount, require_confirm, split, trim_to_rows, ui


async def confirm_source_account(ctx, source_account: bytes):
    text = Text("Confirm operation", ui.ICON_CONFIRM, ui.GREEN)
    text.bold("Source account:")
    text.mono(*split(source_account))
    await require_confirm(ctx, text, ButtonRequestType.ConfirmOutput)


async def confirm_allow_trust_op(ctx, op: StellarAllowTrustOp):
    if op.is_authorized:
        t = "Allow Trust"
    else:
        t = "Revoke Trust"
    text = Text("Confirm operation", ui.ICON_CONFIRM, ui.GREEN)
    text.bold(t)
    text.normal("of %s by:" % op.asset_code)
    text.mono(*split(trim_to_rows(op.trusted_account, 3)))

    await require_confirm(ctx, text, ButtonRequestType.ConfirmOutput)


async def confirm_account_merge_op(ctx, op: StellarAccountMergeOp):
    text = Text("Confirm operation", ui.ICON_CONFIRM, ui.GREEN)
    text.bold("Account Merge")
    text.normal("All XLM will be sent to:")
    text.mono(*split(trim_to_rows(op.destination_account, 3)))
    await require_confirm(ctx, text, ButtonRequestType.ConfirmOutput)


async def confirm_bump_sequence_op(ctx, op: StellarBumpSequenceOp):
    text = Text("Confirm operation", ui.ICON_CONFIRM, ui.GREEN)
    text.bold("Bump Sequence")
    text.normal("Set sequence to")
    text.mono(str(op.bump_to))
    await require_confirm(ctx, text, ButtonRequestType.ConfirmOutput)


async def confirm_change_trust_op(ctx, op: StellarChangeTrustOp):
    if op.limit == 0:
        t = "Delete Trust"
    else:
        t = "Add Trust"
    text = Text("Confirm operation", ui.ICON_CONFIRM, ui.GREEN)
    text.bold(t)
    text.normal("Asset: %s" % op.asset.code)
    text.normal("Amount: %s" % format_amount(op.limit, ticker=False))
    await require_confirm(ctx, text, ButtonRequestType.ConfirmOutput)
    await confirm_asset_issuer(ctx, op.asset)


async def confirm_create_account_op(ctx, op: StellarCreateAccountOp):
    text = Text("Confirm operation", ui.ICON_CONFIRM, ui.GREEN)
    text.bold("Create Account")
    text.normal("with %s" % format_amount(op.starting_balance))
    text.mono(*split(trim_to_rows(op.new_account, 3)))
    await require_confirm(ctx, text, ButtonRequestType.ConfirmOutput)


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
    text = Text("Confirm operation", ui.ICON_CONFIRM, ui.GREEN)
    text.bold(title)
    text.normal(
        "Sell %s %s" % (format_amount(op.amount, ticker=False), op.selling_asset.code)
    )
    text.normal("For %f" % (op.price_n / op.price_d))
    text.normal("Per %s" % format_asset_code(op.buying_asset))
    await require_confirm(ctx, text, ButtonRequestType.ConfirmOutput)
    await confirm_asset_issuer(ctx, op.selling_asset)
    await confirm_asset_issuer(ctx, op.buying_asset)


async def confirm_manage_data_op(ctx, op: StellarManageDataOp):
    from trezor.crypto.hashlib import sha256

    if op.value:
        title = "Set"
    else:
        title = "Clear"
    text = Text("Confirm operation", ui.ICON_CONFIRM, ui.GREEN)
    text.bold("%s data value key" % title)
    text.mono(*split(op.key))
    await require_confirm(ctx, text, ButtonRequestType.ConfirmOutput)
    if op.value:
        digest = sha256(op.value).digest()
        digest_str = hexlify(digest).decode()
        text = Text("Confirm operation", ui.ICON_CONFIRM, ui.GREEN)
        text.bold("Value (SHA-256):")
        text.mono(*split(digest_str))
        await require_confirm(ctx, text, ButtonRequestType.ConfirmOutput)


async def confirm_path_payment_op(ctx, op: StellarPathPaymentOp):
    text = Text("Confirm operation", ui.ICON_CONFIRM, ui.GREEN)
    text.bold("Path Pay %s" % format_amount(op.destination_amount, ticker=False))
    text.bold("%s to:" % format_asset_code(op.destination_asset))
    text.mono(*split(trim_to_rows(op.destination_account, 3)))
    await require_confirm(ctx, text, ButtonRequestType.ConfirmOutput)
    await confirm_asset_issuer(ctx, op.destination_asset)
    # confirm what the sender is using to pay
    text = Text("Confirm operation", ui.ICON_CONFIRM, ui.GREEN)
    text.normal("Pay using")
    text.bold(format_amount(op.send_max, ticker=False))
    text.bold(format_asset_code(op.send_asset))
    text.normal("This amount is debited")
    text.normal("from your account.")
    await require_confirm(ctx, text, ButtonRequestType.ConfirmOutput)
    await confirm_asset_issuer(ctx, op.send_asset)


async def confirm_payment_op(ctx, op: StellarPaymentOp):
    text = Text("Confirm operation", ui.ICON_CONFIRM, ui.GREEN)
    text.bold("Pay %s" % format_amount(op.amount, ticker=False))
    text.bold("%s to:" % format_asset_code(op.asset))
    text.mono(*split(trim_to_rows(op.destination_account, 3)))
    await require_confirm(ctx, text, ButtonRequestType.ConfirmOutput)
    await confirm_asset_issuer(ctx, op.asset)


async def confirm_set_options_op(ctx, op: StellarSetOptionsOp):
    if op.inflation_destination_account:
        text = Text("Confirm operation", ui.ICON_CONFIRM, ui.GREEN)
        text.bold("Set Inflation Destination")
        text.mono(*split(op.inflation_destination_account))
        await require_confirm(ctx, text, ButtonRequestType.ConfirmOutput)
    if op.clear_flags:
        t = _format_flags(op.clear_flags)
        text = Text("Confirm operation", ui.ICON_CONFIRM, ui.GREEN)
        text.bold("Clear Flags")
        text.mono(*t)
        await require_confirm(ctx, text, ButtonRequestType.ConfirmOutput)
    if op.set_flags:
        t = _format_flags(op.set_flags)
        text = Text("Confirm operation", ui.ICON_CONFIRM, ui.GREEN)
        text.bold("Set Flags")
        text.mono(*t)
        await require_confirm(ctx, text, ButtonRequestType.ConfirmOutput)
    thresholds = _format_thresholds(op)
    if thresholds:
        text = Text("Confirm operation", ui.ICON_CONFIRM, ui.GREEN)
        text.bold("Account Thresholds")
        text.mono(*thresholds)
        await require_confirm(ctx, text, ButtonRequestType.ConfirmOutput)
    if op.home_domain:
        text = Text("Confirm operation", ui.ICON_CONFIRM, ui.GREEN)
        text.bold("Home Domain")
        text.mono(*split(op.home_domain))
        await require_confirm(ctx, text, ButtonRequestType.ConfirmOutput)
    if op.signer_type is not None:
        if op.signer_weight > 0:
            t = "Add Signer (%s)"
        else:
            t = "Remove Signer (%s)"
        if op.signer_type == consts.SIGN_TYPE_ACCOUNT:
            text = Text("Confirm operation", ui.ICON_CONFIRM, ui.GREEN)
            text.bold(t % "acc")
            text.mono(*split(helpers.address_from_public_key(op.signer_key)))
            await require_confirm(ctx, text, ButtonRequestType.ConfirmOutput)
        elif op.signer_type in (consts.SIGN_TYPE_PRE_AUTH, consts.SIGN_TYPE_HASH):
            if op.signer_type == consts.SIGN_TYPE_PRE_AUTH:
                signer_type = "auth"
            else:
                signer_type = "hash"
            text = Text("Confirm operation", ui.ICON_CONFIRM, ui.GREEN)
            text.bold(t % signer_type)
            text.mono(*split(hexlify(op.signer_key).decode()))
            await require_confirm(ctx, text, ButtonRequestType.ConfirmOutput)
        else:
            raise ProcessError("Stellar: invalid signer type")


def _format_thresholds(op: StellarSetOptionsOp) -> tuple:
    text = ()
    if op.master_weight is not None:
        text += ("Master Weight: %d" % op.master_weight,)
    if op.low_threshold is not None:
        text += ("Low: %d" % op.low_threshold,)
    if op.medium_threshold is not None:
        text += ("Medium: %d" % op.medium_threshold,)
    if op.high_threshold is not None:
        text += ("High: %d" % op.high_threshold,)
    return text


def _format_flags(flags: int) -> tuple:
    if flags > consts.FLAGS_MAX_SIZE:
        raise ProcessError("Stellar: invalid flags")
    text = ()
    if flags & consts.FLAG_AUTH_REQUIRED:
        text += ("AUTH_REQUIRED",)
    if flags & consts.FLAG_AUTH_REVOCABLE:
        text += ("AUTH_REVOCABLE",)
    if flags & consts.FLAG_AUTH_IMMUTABLE:
        text += ("AUTH_IMMUTABLE",)
    return text


def format_asset_code(asset: StellarAssetType) -> str:
    if asset is None or asset.type == consts.ASSET_TYPE_NATIVE:
        return "XLM (native)"
    return asset.code


async def confirm_asset_issuer(ctx, asset: StellarAssetType):
    if asset is None or asset.type == consts.ASSET_TYPE_NATIVE:
        return
    text = Text("Confirm issuer", ui.ICON_CONFIRM, ui.GREEN)
    text.bold("%s issuer:" % asset.code)
    text.mono(*split(asset.issuer))
    await require_confirm(ctx, text, ButtonRequestType.ConfirmOutput)
