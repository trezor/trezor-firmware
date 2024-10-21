from typing import TYPE_CHECKING
from ubinascii import hexlify

from trezor import TR
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
        StellarClaimClaimableBalanceOp,
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
        TR.stellar__confirm_operation,
        source_account,
        description=TR.stellar__source_account,
        br_name="op_source_account",
    )


async def confirm_allow_trust_op(op: StellarAllowTrustOp) -> None:
    await confirm_properties(
        "op_allow_trust",
        TR.stellar__allow_trust if op.is_authorized else TR.stellar__revoke_trust,
        (
            (TR.stellar__asset, op.asset_code),
            (TR.stellar__trusted_account, op.trusted_account),
        ),
    )


async def confirm_account_merge_op(op: StellarAccountMergeOp) -> None:
    await confirm_address(
        TR.stellar__account_merge,
        op.destination_account,
        description=TR.stellar__all_will_be_sent_to,
        br_name="op_account_merge",
    )


async def confirm_bump_sequence_op(op: StellarBumpSequenceOp) -> None:
    await confirm_metadata(
        "op_bump",
        TR.stellar__bump_sequence,
        TR.stellar__set_sequence_to_template,
        str(op.bump_to),
    )


async def confirm_change_trust_op(op: StellarChangeTrustOp) -> None:
    await confirm_amount(
        TR.stellar__delete_trust if op.limit == 0 else TR.stellar__add_trust,
        format_amount(op.limit, op.asset),
        TR.stellar__limit,
        "op_change_trust",
    )
    await confirm_asset_issuer(op.asset)


async def confirm_create_account_op(op: StellarCreateAccountOp) -> None:
    await confirm_properties(
        "op_create_account",
        TR.stellar__create_account,
        (
            (TR.words__account, op.new_account),
            (TR.stellar__initial_balance, format_amount(op.starting_balance)),
        ),
    )


async def confirm_create_passive_sell_offer_op(
    op: StellarCreatePassiveSellOfferOp,
) -> None:
    text = (
        TR.stellar__delete_passive_offer
        if op.amount == 0
        else TR.stellar__new_passive_offer
    )
    await _confirm_offer(text, op)


async def confirm_manage_buy_offer_op(op: StellarManageBuyOfferOp) -> None:
    await _confirm_manage_offer_op_common(op)


async def confirm_manage_sell_offer_op(op: StellarManageSellOfferOp) -> None:
    await _confirm_manage_offer_op_common(op)


async def _confirm_manage_offer_op_common(
    op: StellarManageBuyOfferOp | StellarManageSellOfferOp,
) -> None:
    if op.offer_id == 0:
        text = TR.stellar__new_offer
    else:
        text = f"{TR.stellar__delete if op.amount == 0 else TR.stellar__update} #{op.offer_id}"
    await _confirm_offer(text, op)


async def _confirm_offer(
    title: str,
    op: (
        StellarCreatePassiveSellOfferOp
        | StellarManageSellOfferOp
        | StellarManageBuyOfferOp
    ),
) -> None:
    from trezor.messages import StellarManageBuyOfferOp

    from ..layout import format_asset

    buying_asset = op.buying_asset  # local_cache_attribute
    selling_asset = op.selling_asset  # local_cache_attribute

    if StellarManageBuyOfferOp.is_type_of(op):
        buying = (TR.stellar__buying, format_amount(op.amount, buying_asset))
        selling = (TR.stellar__selling, format_asset(selling_asset))
        price = (
            TR.stellar__price_per_template.format(format_asset(selling_asset)),
            str(op.price_n / op.price_d),
        )
        await confirm_properties(
            "op_offer",
            title,
            (buying, selling, price),
        )
    else:
        selling = (TR.stellar__selling, format_amount(op.amount, selling_asset))
        buying = (TR.stellar__buying, format_asset(buying_asset))
        price = (
            TR.stellar__price_per_template.format(format_asset(buying_asset)),
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
            TR.stellar__set_data,
            ((TR.stellar__key, op.key), (TR.stellar__value_sha256, digest)),
        )
    else:
        await confirm_metadata(
            "op_data",
            TR.stellar__clear_data,
            TR.stellar__wanna_clean_value_key_template,
            op.key,
        )


async def confirm_path_payment_strict_receive_op(
    op: StellarPathPaymentStrictReceiveOp,
) -> None:
    await confirm_output(
        op.destination_account,
        format_amount(op.destination_amount, op.destination_asset),
        title=TR.stellar__path_pay,
    )
    await confirm_asset_issuer(op.destination_asset)
    # confirm what the sender is using to pay
    await confirm_amount(
        TR.stellar__debited_amount,
        format_amount(op.send_max, op.send_asset),
        TR.stellar__pay_at_most,
        "op_path_payment_strict_receive",
    )
    await confirm_asset_issuer(op.send_asset)


async def confirm_path_payment_strict_send_op(
    op: StellarPathPaymentStrictSendOp,
) -> None:
    await confirm_output(
        op.destination_account,
        format_amount(op.destination_min, op.destination_asset),
        title=TR.stellar__path_pay_at_least,
    )
    await confirm_asset_issuer(op.destination_asset)
    # confirm what the sender is using to pay
    await confirm_amount(
        TR.stellar__debited_amount,
        format_amount(op.send_amount, op.send_asset),
        TR.stellar__pay,
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
            TR.stellar__inflation,
            op.inflation_destination_account,
            description=TR.stellar__destination,
            br_name="op_inflation",
        )

    if op.clear_flags:
        t = _format_flags(op.clear_flags)
        await confirm_text("op_set_options", TR.stellar__clear_flags, data=t)

    if op.set_flags:
        t = _format_flags(op.set_flags)
        await confirm_text("op_set_options", TR.stellar__set_flags, data=t)

    thresholds: list[tuple[str, str]] = []
    append = thresholds.append  # local_cache_attribute
    if op.master_weight is not None:
        append((TR.stellar__master_weight, str(op.master_weight)))
    if op.low_threshold is not None:
        append((TR.stellar__low, str(op.low_threshold)))
    if op.medium_threshold is not None:
        append((TR.stellar__medium, str(op.medium_threshold)))
    if op.high_threshold is not None:
        append((TR.stellar__high, str(op.high_threshold)))

    if thresholds:
        await confirm_properties(
            "op_thresholds", TR.stellar__account_thresholds, thresholds
        )

    if op.home_domain:
        await confirm_text("op_home_domain", TR.stellar__home_domain, op.home_domain)
    signer_type = op.signer_type  # local_cache_attribute
    signer_key = op.signer_key  # local_cache_attribute

    if signer_type is not None:
        if signer_key is None or op.signer_weight is None:
            raise DataError("Stellar: invalid signer option data.")

        if op.signer_weight > 0:
            title = TR.stellar__add_signer
        else:
            title = TR.stellar__remove_signer
        data: str | bytes = ""
        if signer_type == StellarSignerType.ACCOUNT:
            description = f"{TR.words__account}:"
            data = helpers.address_from_public_key(signer_key)
        elif signer_type == StellarSignerType.PRE_AUTH:
            description = TR.stellar__preauth_transaction
            data = signer_key
        elif signer_type == StellarSignerType.HASH:
            description = TR.stellar__hash
            data = signer_key
        else:
            raise ProcessError("Stellar: invalid signer type")

        await confirm_blob(
            "op_signer",
            title=title,
            description=description,
            data=data,
        )


async def confirm_claim_claimable_balance_op(
    op: StellarClaimClaimableBalanceOp,
) -> None:
    balance_id = hexlify(op.balance_id).decode()
    await confirm_metadata(
        "op_claim_claimable_balance",
        TR.stellar__claim_claimable_balance,
        TR.stellar__balance_id + ": {}",
        balance_id,
    )


def _format_flags(flags: int) -> str:
    from .. import consts

    if flags > consts.FLAGS_MAX_SIZE:
        raise ProcessError("Stellar: invalid flags")
    flags_set: list[str] = []
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
        TR.stellar__confirm_issuer,
        asset.issuer,
        description=TR.stellar__issuer_template.format(asset.code),
        br_name="confirm_asset_issuer",
    )
