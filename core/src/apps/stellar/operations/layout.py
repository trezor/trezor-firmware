from typing import TYPE_CHECKING

from trezor import TR
from trezor.ui.layouts import (
    confirm_address,
    confirm_properties,
    confirm_stellar_output,
    confirm_stellar_output_amount,
    confirm_value,
)
from trezor.wire import DataError, ProcessError

from ..layout import confirm_invocation, confirm_invoke_contract
from ..tokens import NATIVE_TOKEN, StellarToken

if TYPE_CHECKING:
    from buffer_types import AnyBytes, StrOrBytes

    from trezor.messages import (
        StellarAccountMergeOp,
        StellarAllowTrustOp,
        StellarAsset,
        StellarBumpSequenceOp,
        StellarChangeTrustOp,
        StellarClaimClaimableBalanceOp,
        StellarCreateAccountOp,
        StellarCreatePassiveSellOfferOp,
        StellarHostFunction,
        StellarInvokeHostFunctionOp,
        StellarManageBuyOfferOp,
        StellarManageDataOp,
        StellarManageSellOfferOp,
        StellarPathPaymentStrictReceiveOp,
        StellarPathPaymentStrictSendOp,
        StellarPaymentOp,
        StellarSetOptionsOp,
        StellarSorobanAuthorizationEntry,
        StellarSorobanDelegateSignature,
    )
    from trezor.ui.layouts import PropertyType


async def confirm_source_account(source_account: str) -> None:
    await confirm_address(
        TR.stellar__confirm_operation,
        source_account,
        description=TR.stellar__source_account,
        br_name="op_source_account",
        verb=TR.buttons__continue,
    )


async def confirm_allow_trust_op(op: StellarAllowTrustOp) -> None:
    await confirm_properties(
        "op_allow_trust",
        TR.stellar__allow_trust if op.is_authorized else TR.stellar__revoke_trust,
        (
            (TR.words__asset, op.asset_code, True),
            (TR.stellar__trusted_account, op.trusted_account, True),
        ),
        verb=TR.buttons__continue,
    )


async def confirm_account_merge_op(
    op: StellarAccountMergeOp, output_index: int
) -> None:
    await confirm_address(
        TR.stellar__account_merge,
        op.destination_account,
        subtitle=f"{TR.words__recipient} #{output_index + 1}",
        description=TR.stellar__all_will_be_sent_to,
        br_name="op_account_merge",
        verb=TR.buttons__continue,
    )


async def confirm_bump_sequence_op(op: StellarBumpSequenceOp) -> None:
    await confirm_value(
        TR.stellar__bump_sequence,
        TR.stellar__set_sequence_to_template.format(str(op.bump_to)),
        description="",
        br_name="op_bump",
        is_data=False,
        verb=TR.buttons__continue,
    )


async def confirm_change_trust_op(op: StellarChangeTrustOp) -> None:
    await confirm_value(
        TR.stellar__delete_trust if op.limit == 0 else TR.stellar__add_trust,
        StellarToken.from_asset(op.asset).format(op.limit),
        description=TR.stellar__limit,
        br_name="op_change_trust",
        is_data=False,
        verb=TR.buttons__continue,
    )

    await confirm_asset_issuer(op.asset)


async def confirm_create_account_op(
    op: StellarCreateAccountOp, output_index: int
) -> None:
    token = NATIVE_TOKEN
    await confirm_stellar_output(
        op.new_account,
        token.format(op.starting_balance),
        output_index=output_index,
        token=token,
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

    buying_asset = op.buying_asset  # local_cache_attribute
    selling_asset = op.selling_asset  # local_cache_attribute
    buying_token = StellarToken.from_asset(buying_asset)
    selling_token = StellarToken.from_asset(selling_asset)

    buying: PropertyType
    selling: PropertyType
    price: PropertyType

    if StellarManageBuyOfferOp.is_type_of(op):
        buying = (
            TR.stellar__buying,
            buying_token.format(op.amount),
            False,
        )
        selling = (
            TR.stellar__selling,
            selling_token.symbol,
            False,
        )
        price = (
            TR.stellar__price_per_template.format(selling_token.symbol),
            str(op.price_n / op.price_d),
            False,
        )
        await confirm_properties(
            "op_offer",
            title,
            (buying, selling, price),
            verb=TR.buttons__continue,
        )
    else:
        selling = (
            TR.stellar__selling,
            selling_token.format(op.amount),
            False,
        )
        buying = (TR.stellar__buying, buying_token.symbol, False)
        price = (
            TR.stellar__price_per_template.format(buying_token.symbol),
            str(op.price_n / op.price_d),
            False,
        )
        await confirm_properties(
            "op_offer",
            title,
            (selling, buying, price),
            verb=TR.buttons__continue,
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
            ((TR.stellar__key, op.key, True), (TR.stellar__value_sha256, digest, True)),
            verb=TR.buttons__continue,
        )
    else:
        await confirm_value(
            TR.stellar__clear_data,
            TR.stellar__wanna_clean_value_key_template.format(op.key),
            description="",
            br_name="op_data",
            is_data=False,
            verb=TR.buttons__continue,
        )


async def confirm_path_payment_strict_receive_op(
    op: StellarPathPaymentStrictReceiveOp,
    output_index: int,
) -> None:
    destination_token = StellarToken.from_asset(op.destination_asset)
    send_token = StellarToken.from_asset(op.send_asset)
    await confirm_stellar_output(
        op.destination_account,
        destination_token.format(op.destination_amount),
        output_index,
        destination_token,
        address_description=TR.stellar__path_pay,
        amount_description=TR.stellar__path_pay,
    )

    await confirm_stellar_output_amount(
        TR.stellar__debited_amount,
        f"{TR.words__recipient} #{output_index + 1}",
        send_token.format(op.send_max),
        send_token,
        TR.stellar__pay_at_most,
    )


async def confirm_path_payment_strict_send_op(
    op: StellarPathPaymentStrictSendOp,
    output_index: int,
) -> None:
    destination_token = StellarToken.from_asset(op.destination_asset)
    send_token = StellarToken.from_asset(op.send_asset)
    await confirm_stellar_output(
        op.destination_account,
        destination_token.format(op.destination_min),
        output_index,
        destination_token,
        address_description=TR.stellar__path_pay_at_least,
        amount_description=TR.stellar__path_pay_at_least,
    )

    await confirm_stellar_output_amount(
        TR.stellar__debited_amount,
        f"{TR.words__recipient} #{output_index + 1}",
        send_token.format(op.send_amount),
        send_token,
        TR.stellar__pay,
    )


async def confirm_payment_op(op: StellarPaymentOp, output_index: int) -> None:
    token = StellarToken.from_asset(op.asset)
    await confirm_stellar_output(
        op.destination_account,
        token.format(op.amount),
        output_index,
        token,
    )


async def confirm_set_options_op(op: StellarSetOptionsOp) -> None:
    from trezor.enums import StellarSignerType
    from trezor.ui.layouts import confirm_blob

    from .. import helpers

    if op.inflation_destination_account:
        await confirm_address(
            TR.stellar__inflation,
            op.inflation_destination_account,
            description=TR.stellar__destination,
            br_name="op_inflation",
            verb=TR.buttons__continue,
        )

    if op.clear_flags:
        t = _format_flags(op.clear_flags)
        await confirm_value(
            title=TR.stellar__clear_flags,
            value=t,
            description="",
            br_name="op_clear_flags",
            is_data=False,
            verb=TR.buttons__continue,
        )

    if op.set_flags:
        t = _format_flags(op.set_flags)
        await confirm_value(
            title=TR.stellar__set_flags,
            value=t,
            description="",
            br_name="op_set_flags",
            is_data=False,
            verb=TR.buttons__continue,
        )

    thresholds: list[PropertyType] = []
    append = thresholds.append  # local_cache_attribute
    if op.master_weight is not None:
        append((TR.stellar__master_weight, str(op.master_weight), True))
    if op.low_threshold is not None:
        append((TR.stellar__low, str(op.low_threshold), True))
    if op.medium_threshold is not None:
        append((TR.stellar__medium, str(op.medium_threshold), True))
    if op.high_threshold is not None:
        append((TR.stellar__high, str(op.high_threshold), True))

    if thresholds:
        await confirm_properties(
            "op_thresholds",
            TR.stellar__account_thresholds,
            thresholds,
            verb=TR.buttons__continue,
        )

    if op.home_domain:
        await confirm_value(
            title=TR.stellar__home_domain,
            value=op.home_domain,
            description="",
            br_name="op_home_domain",
            is_data=False,
            verb=TR.buttons__continue,
        )
    signer_type = op.signer_type  # local_cache_attribute
    signer_key = op.signer_key  # local_cache_attribute

    if signer_type is not None:
        if signer_key is None or op.signer_weight is None:
            raise DataError("Stellar: invalid signer option data.")

        if op.signer_weight > 0:
            title = TR.stellar__add_signer
        else:
            title = TR.stellar__remove_signer
        data: StrOrBytes = ""
        if signer_type == StellarSignerType.ACCOUNT:
            description = TR.words__account
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
            verb=TR.buttons__continue,
        )


async def confirm_claim_claimable_balance_op(
    op: StellarClaimClaimableBalanceOp,
) -> None:
    balance_id = op.balance_id.hex()
    await confirm_properties(
        "op_claim_claimable_balance",
        TR.stellar__claim_claimable_balance,
        ((TR.stellar__balance_id, balance_id, True),),
        verb=TR.buttons__continue,
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
        verb=TR.buttons__continue,
    )


def _is_root_auth_entry(
    auth_entry: StellarSorobanAuthorizationEntry, invoked_fn: StellarHostFunction
) -> bool:
    from trezor.enums import (
        StellarHostFunctionType,
        StellarSorobanAuthorizedFunctionType,
    )

    from ..writers import write_invoke_contract_args

    auth_fn = auth_entry.root_invocation.function

    if (
        auth_fn.type
        == StellarSorobanAuthorizedFunctionType.SOROBAN_AUTHORIZED_FUNCTION_TYPE_CONTRACT_FN
        and invoked_fn.type
        == StellarHostFunctionType.HOST_FUNCTION_TYPE_INVOKE_CONTRACT
    ):
        if auth_fn.contract_fn is None or invoked_fn.invoke_contract is None:
            return False

        b1 = bytearray()
        write_invoke_contract_args(b1, auth_fn.contract_fn)
        b2 = bytearray()
        write_invoke_contract_args(b2, invoked_fn.invoke_contract)

        return b1 == b2

    return False


async def confirm_invoke_host_function_op(
    op: StellarInvokeHostFunctionOp, tx_source_account: str, network_id: AnyBytes
) -> None:
    from trezor.enums import StellarHostFunctionType, StellarSorobanCredentialsType
    from trezor.ui.layouts import should_show_more

    function = op.function

    # the account whose signature authorizes the operation anyway: its
    # explicit source account, or the transaction's otherwise
    source_account = op.source_account or tx_source_account

    if function.type == StellarHostFunctionType.HOST_FUNCTION_TYPE_INVOKE_CONTRACT:
        if function.invoke_contract is None:
            raise DataError("Stellar: missing invoke_contract")

        await confirm_invoke_contract(
            function.invoke_contract,
            network_id,
            source_account,
        )
    else:
        raise ProcessError("Stellar: unsupported host function type")

    # Auth entries fall into two kinds by credential type:
    #
    # - SOURCE_ACCOUNT credentials are authorized by the signature the device
    #   produces over the transaction envelope. Approving that signature approves
    #   these entries, so we must always show them for confirmation.
    #
    # - ADDRESS* credentials are authorized by a separate signature over the
    #   ENVELOPE_TYPE_SOROBAN_AUTHORIZATION* preimage, which must already
    #   be present in the entry at the time of signing the transaction.
    #   Entries of this type are therefore hidden behind an opt-in and only
    #   shown for information; the user does not need to review them to sign safely.

    shown = 0
    non_src_entries = []

    for auth_entry in op.auth:
        if (
            auth_entry.credentials.type
            == StellarSorobanCredentialsType.SOROBAN_CREDENTIALS_SOURCE_ACCOUNT
        ):
            shown += 1
            await _confirm_auth_entry(
                auth_entry,
                shown,
                network_id,
                source_account,
                is_root=_is_root_auth_entry(auth_entry, function),
            )
        else:
            non_src_entries.append(auth_entry)

    show_non_src = non_src_entries and await should_show_more(
        TR.stellar__ext_auth,
        ((TR.stellar__ext_auth_message, False),),
        button_text=TR.buttons__show_all,
    )
    if show_non_src:
        for auth_entry in non_src_entries:
            shown += 1
            await _confirm_auth_entry(
                auth_entry,
                shown,
                network_id,
                source_account,
                is_root=_is_root_auth_entry(auth_entry, function),
            )


async def _confirm_auth_entry(
    auth: StellarSorobanAuthorizationEntry,
    position: int,
    network_id: AnyBytes,
    source_account: str,
    is_root: bool = False,
) -> None:
    from trezor.enums import StellarSorobanCredentialsType

    creds = auth.credentials
    # SOURCE_ACCOUNT credentials authorize the tree through the effective
    # operation source; address credentials name their authorizing party.
    if creds.type == StellarSorobanCredentialsType.SOROBAN_CREDENTIALS_SOURCE_ACCOUNT:
        authorizing_address = source_account
    elif creds.type == StellarSorobanCredentialsType.SOROBAN_CREDENTIALS_ADDRESS_V2:
        if creds.address_v2 is None:
            raise DataError("Stellar: missing address_v2 credentials")
        authorizing_address = creds.address_v2.address
        await _confirm_authorizing_address(
            f"{TR.words__authorization} #{position}", authorizing_address
        )
    elif (
        creds.type
        == StellarSorobanCredentialsType.SOROBAN_CREDENTIALS_ADDRESS_WITH_DELEGATES
    ):
        if creds.address_with_delegates is None:
            raise DataError("Stellar: missing address_with_delegates credentials")
        with_delegates = creds.address_with_delegates
        authorizing_address = with_delegates.address_credentials.address
        title = f"{TR.words__authorization} #{position}"
        await _confirm_authorizing_address(title, authorizing_address)
        await _confirm_delegated_signers(with_delegates.delegates, title)
    else:
        raise ProcessError("Stellar: unsupported credentials type")

    # Show the whole authorized invocation tree starting from its root (not just the
    # nested sub-invocations), so the user sees exactly what this signature authorizes.
    await confirm_invocation(
        auth.root_invocation,
        f"#{position}",
        network_id,
        authorizing_address,
        is_root=is_root,
    )


async def _confirm_authorizing_address(title: str, address: str) -> None:
    await confirm_address(
        title,
        address,
        description=TR.words__address,
        br_name="op_auth_entry_address",
    )


async def _confirm_delegated_signers(
    delegates: list[StellarSorobanDelegateSignature],
    title: str,
    path: str = "",
) -> None:
    """Confirm the delegated signers of an authorization entry, recursively.

    Every delegate is labeled by its dot-delimited position in the delegation
    tree ("1", "1.2", ...), mirroring how sub-invocations are labeled.
    """
    for i, delegate in enumerate(delegates):
        delegate_path = f"{path}{i + 1}"
        await confirm_address(
            title,
            delegate.address,
            description=f"{TR.stellar__delegated_signer} {delegate_path}",
            br_name="op_auth_entry_delegate",
        )
        await _confirm_delegated_signers(
            delegate.nested_delegates, title, f"{delegate_path}."
        )
