from typing import TYPE_CHECKING

from trezor.ui.layouts import (
    confirm_address,
    confirm_amount,
    confirm_metadata,
    confirm_output,
    confirm_properties,
)
from trezor.wire import DataError, ProcessError

from ..layout import format_amount

if TYPE_CHECKING:

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


async def confirm_source_account(source_account: str) -> None:
    await confirm_address(
        "Confirm operation",
        source_account,
        "Source account:",
        "op_source_account",
    )


async def confirm_allow_trust_op(op: StellarAllowTrustOp) -> None:
    await confirm_properties(
        "op_allow_trust",
        "Allow trust" if op.is_authorized else "Revoke trust",
        (
            ("Asset", op.asset_code),
            ("Trusted Account", op.trusted_account),
        ),
    )


async def confirm_account_merge_op(op: StellarAccountMergeOp) -> None:
    await confirm_address(
        "Account Merge",
        op.destination_account,
        "All XLM will be sent to:",
        "op_account_merge",
    )


async def confirm_bump_sequence_op(op: StellarBumpSequenceOp) -> None:
    await confirm_metadata(
        "op_bump",
        "Bump Sequence",
        "Set sequence to {}?",
        str(op.bump_to),
    )


async def confirm_change_trust_op(op: StellarChangeTrustOp) -> None:
    await confirm_amount(
        "Delete trust" if op.limit == 0 else "Add trust",
        format_amount(op.limit, op.asset),
        "Limit:",
        "op_change_trust",
    )
    await confirm_asset_issuer(op.asset)


async def confirm_create_account_op(op: StellarCreateAccountOp) -> None:
    await confirm_properties(
        "op_create_account",
        "Create Account",
        (
            ("Account", op.new_account),
            ("Initial Balance", format_amount(op.starting_balance)),
        ),
    )


async def confirm_create_passive_sell_offer_op(
    op: StellarCreatePassiveSellOfferOp,
) -> None:
    text = "Delete Passive Offer" if op.amount == 0 else "New Passive Offer"
    await _confirm_offer(text, op)


async def confirm_manage_buy_offer_op(op: StellarManageBuyOfferOp) -> None:
    await _confirm_manage_offer_op_common(op)


async def confirm_manage_sell_offer_op(op: StellarManageSellOfferOp) -> None:
    await _confirm_manage_offer_op_common(op)


async def _confirm_manage_offer_op_common(
    op: StellarManageBuyOfferOp | StellarManageSellOfferOp,
) -> None:
    if op.offer_id == 0:
        text = "New Offer"
    else:
        text = f"{'Delete' if op.amount == 0 else 'Update'} #{op.offer_id}"
    await _confirm_offer(text, op)


async def _confirm_offer(
    title: str,
    op: StellarCreatePassiveSellOfferOp
    | StellarManageSellOfferOp
    | StellarManageBuyOfferOp,
) -> None:
    from trezor.messages import StellarManageBuyOfferOp

    from ..layout import format_asset

    buying_asset = op.buying_asset  # local_cache_attribute
    selling_asset = op.selling_asset  # local_cache_attribute

    if StellarManageBuyOfferOp.is_type_of(op):
        buying = ("Buying:", format_amount(op.amount, buying_asset))
        selling = ("Selling:", format_asset(selling_asset))
        price = (
            f"Price per {format_asset(selling_asset)}:",
            str(op.price_n / op.price_d),
        )
        await confirm_properties(
            "op_offer",
            title,
            (buying, selling, price),
        )
    else:
        selling = ("Selling:", format_amount(op.amount, selling_asset))
        buying = ("Buying:", format_asset(buying_asset))
        price = (
            f"Price per {format_asset(buying_asset)}:",
            str(op.price_n / op.price_d),
        )
        await confirm_properties(
            "op_offer",
            title,
            (selling, buying, price),
        )

    await confirm_asset_issuer(selling_asset)
    await confirm_asset_issuer(buying_asset)


async def confirm_manage_data_op(op: StellarManageDataOp) -> None:
    from trezor.crypto.hashlib import sha256

    if op.value:
        digest = sha256(op.value).digest()
        await confirm_properties(
            "op_data",
            "Set data",
            (("Key:", op.key), ("Value (SHA-256):", digest)),
        )
    else:
        await confirm_metadata(
            "op_data",
            "Clear data",
            "Do you want to clear value key {}?",
            op.key,
        )


async def confirm_path_payment_strict_receive_op(
    op: StellarPathPaymentStrictReceiveOp,
) -> None:
    await confirm_output(
        op.destination_account,
        format_amount(op.destination_amount, op.destination_asset),
        title="Path Pay",
    )
    await confirm_asset_issuer(op.destination_asset)
    # confirm what the sender is using to pay
    await confirm_amount(
        "Debited amount",
        format_amount(op.send_max, op.send_asset),
        "Pay at most:",
        "op_path_payment_strict_receive",
    )
    await confirm_asset_issuer(op.send_asset)


async def confirm_path_payment_strict_send_op(
    op: StellarPathPaymentStrictSendOp,
) -> None:
    await confirm_output(
        op.destination_account,
        format_amount(op.destination_min, op.destination_asset),
        title="Path Pay at least",
    )
    await confirm_asset_issuer(op.destination_asset)
    # confirm what the sender is using to pay
    await confirm_amount(
        "Debited amount",
        format_amount(op.send_amount, op.send_asset),
        "Pay:",
        "op_path_payment_strict_send",
    )
    await confirm_asset_issuer(op.send_asset)


async def confirm_payment_op(op: StellarPaymentOp) -> None:
    await confirm_output(
        op.destination_account,
        format_amount(op.amount, op.asset),
    )
    await confirm_asset_issuer(op.asset)


async def confirm_set_options_op(op: StellarSetOptionsOp) -> None:
    from trezor.enums import StellarSignerType
    from trezor.ui.layouts import confirm_blob, confirm_text

    from .. import helpers

    if op.inflation_destination_account:
        await confirm_address(
            "Inflation",
            op.inflation_destination_account,
            "Destination:",
            "op_inflation",
        )

    if op.clear_flags:
        t = _format_flags(op.clear_flags)
        await confirm_text("op_set_options", "Clear flags", data=t)

    if op.set_flags:
        t = _format_flags(op.set_flags)
        await confirm_text("op_set_options", "Set flags", data=t)

    thresholds: list[tuple[str, str]] = []
    append = thresholds.append  # local_cache_attribute
    if op.master_weight is not None:
        append(("Master Weight:", str(op.master_weight)))
    if op.low_threshold is not None:
        append(("Low:", str(op.low_threshold)))
    if op.medium_threshold is not None:
        append(("Medium:", str(op.medium_threshold)))
    if op.high_threshold is not None:
        append(("High:", str(op.high_threshold)))

    if thresholds:
        await confirm_properties("op_thresholds", "Account Thresholds", thresholds)

    if op.home_domain:
        await confirm_text("op_home_domain", "Home Domain", op.home_domain)
    signer_type = op.signer_type  # local_cache_attribute
    signer_key = op.signer_key  # local_cache_attribute

    if signer_type is not None:
        if signer_key is None or op.signer_weight is None:
            raise DataError("Stellar: invalid signer option data.")

        if op.signer_weight > 0:
            title = "Add Signer"
        else:
            title = "Remove Signer"
        data: str | bytes = ""
        if signer_type == StellarSignerType.ACCOUNT:
            description = "Account:"
            data = helpers.address_from_public_key(signer_key)
        elif signer_type == StellarSignerType.PRE_AUTH:
            description = "Pre-auth transaction:"
            data = signer_key
        elif signer_type == StellarSignerType.HASH:
            description = "Hash:"
            data = signer_key
        else:
            raise ProcessError("Stellar: invalid signer type")

        await confirm_blob(
            "op_signer",
            title=title,
            description=description,
            data=data,
        )


def _format_flags(flags: int) -> str:
    from .. import consts

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


async def confirm_asset_issuer(asset: StellarAsset) -> None:
    from trezor.enums import StellarAssetType

    if asset.type == StellarAssetType.NATIVE:
        return
    if asset.issuer is None or asset.code is None:
        raise DataError("Stellar: invalid asset definition")
    await confirm_address(
        "Confirm Issuer",
        asset.issuer,
        f"{asset.code} issuer:",
        "confirm_asset_issuer",
    )
