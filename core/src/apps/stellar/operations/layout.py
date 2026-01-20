from typing import TYPE_CHECKING
from ubinascii import hexlify

from trezor import TR
from trezor.ui.layouts import (
    confirm_address,
    confirm_amount,
    confirm_metadata,
    confirm_output,
    confirm_properties,
    confirm_stellar_output,
    confirm_text,
    should_show_more,
)
from trezor.wire import DataError, ProcessError

from ..layout import format_amount

if TYPE_CHECKING:
    from buffer_types import StrOrBytes

    from trezor.messages import (
        StellarAccountMergeOp,
        StellarAllowTrustOp,
        StellarAsset,
        StellarBumpSequenceOp,
        StellarChangeTrustOp,
        StellarClaimClaimableBalanceOp,
        StellarCreateAccountOp,
        StellarCreatePassiveSellOfferOp,
        StellarInt128Parts,
        StellarInt256Parts,
        StellarInvokeHostFunctionOp,
        StellarManageBuyOfferOp,
        StellarManageDataOp,
        StellarManageSellOfferOp,
        StellarPathPaymentStrictReceiveOp,
        StellarPathPaymentStrictSendOp,
        StellarPaymentOp,
        StellarSCAddress,
        StellarSCVal,
        StellarSetOptionsOp,
        StellarSorobanAuthorizationEntry,
        StellarSorobanAuthorizedInvocation,
        StellarUInt128Parts,
        StellarUInt256Parts,
    )
    from trezor.ui.layouts import PropertyType


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
            (TR.words__asset, op.asset_code, True),
            (TR.stellar__trusted_account, op.trusted_account, True),
        ),
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


async def confirm_create_account_op(
    op: StellarCreateAccountOp, output_index: int
) -> None:
    await confirm_output(
        op.new_account,
        format_amount(op.starting_balance),
        output_index=output_index,
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

    buying: PropertyType
    selling: PropertyType
    price: PropertyType

    if StellarManageBuyOfferOp.is_type_of(op):
        buying = (
            TR.stellar__buying,
            format_amount(op.amount, buying_asset),
            False,
        )
        selling = (
            TR.stellar__selling,
            format_asset(selling_asset),
            False,
        )
        price = (
            TR.stellar__price_per_template.format(format_asset(selling_asset)),
            str(op.price_n / op.price_d),
            False,
        )
        await confirm_properties(
            "op_offer",
            title,
            (buying, selling, price),
        )
    else:
        selling = (
            TR.stellar__selling,
            format_amount(op.amount, selling_asset),
            False,
        )
        buying = (TR.stellar__buying, format_asset(buying_asset), False)
        price = (
            TR.stellar__price_per_template.format(format_asset(buying_asset)),
            str(op.price_n / op.price_d),
            False,
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
            ((TR.stellar__key, op.key, True), (TR.stellar__value_sha256, digest, True)),
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
    output_index: int,
) -> None:
    # TODO: show output index in the subtitle
    await confirm_output(
        op.destination_account,
        format_amount(op.destination_amount, op.destination_asset),
        TR.stellar__path_pay,
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
    output_index: int,
) -> None:
    # TODO: show output index in the subtitle
    await confirm_output(
        op.destination_account,
        format_amount(op.destination_min, op.destination_asset),
        TR.stellar__path_pay_at_least,
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


async def confirm_payment_op(op: StellarPaymentOp, output_index: int) -> None:
    await confirm_stellar_output(
        op.destination_account,
        format_amount(op.amount, op.asset),
        output_index,
        op.asset,
    )


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


async def confirm_invoke_host_function_op(op: StellarInvokeHostFunctionOp) -> None:
    from trezor.enums import StellarHostFunctionType

    function = op.function

    if function.type == StellarHostFunctionType.HOST_FUNCTION_TYPE_INVOKE_CONTRACT:
        if function.invoke_contract is None:
            raise DataError("Stellar: missing invoke_contract")

        invoke = function.invoke_contract
        contract_address = _format_sc_address(invoke.contract_address)

        await confirm_address(
            TR.stellar__invoke_contract,
            contract_address,
            br_name="op_invoke_contract_address",
        )

        await confirm_text(
            "op_invoke_function",
            TR.stellar__function,
            invoke.function_name,
        )

        for i, arg in enumerate(invoke.args):
            arg_str = _format_sc_val(arg)
            await confirm_text(
                "op_invoke_arg",
                title=f"{TR.stellar__argument} #{i + 1}",
                data=arg_str,
            )

        for auth_entry in op.auth:
            await _confirm_auth_entry(auth_entry)
    else:
        raise ProcessError("Stellar: unsupported host function type")


async def _confirm_auth_entry(auth: StellarSorobanAuthorizationEntry) -> None:
    from trezor.enums import StellarSorobanCredentialsType

    creds = auth.credentials

    # Skip non-SOURCE_ACCOUNT entries. When credentials.type is ADDRESS,
    # it means a different address is authorizing with their own signature.
    # Trezor only signs for the source account, so we don't need to display
    # or confirm authorization entries that won't be signed by this device.
    if creds.type != StellarSorobanCredentialsType.SOROBAN_CREDENTIALS_SOURCE_ACCOUNT:
        return

    # Check if there are nested sub-invocations to display
    invocation = auth.root_invocation
    if invocation.sub_invocations:
        await _confirm_nested_invocations(invocation.sub_invocations)


async def _confirm_nested_invocations(
    sub_invocations: list[StellarSorobanAuthorizedInvocation],
) -> None:
    """Prompt user to view nested authorization details."""

    sub_count = len(sub_invocations)
    hint = TR.stellar__contains_x_sub_invocations_template.format(sub_count)

    if await should_show_more(
        TR.stellar__nested_authorization,
        [(hint, False)],
        br_name="op_auth_nested",
    ):
        for i, sub in enumerate(sub_invocations):
            await _confirm_invocation(sub, i)


async def _confirm_invocation(
    invocation: StellarSorobanAuthorizedInvocation,
    index: int,
) -> None:
    """Confirm an authorized invocation and its sub-invocations recursively."""
    from trezor.enums import StellarSorobanAuthorizedFunctionType

    func = invocation.function
    title = f"{TR.stellar__nested_authorization} #{index + 1}"

    if (
        func.type
        == StellarSorobanAuthorizedFunctionType.SOROBAN_AUTHORIZED_FUNCTION_TYPE_CONTRACT_FN
    ):
        if func.contract_fn is None:
            raise DataError("Stellar: missing contract_fn")

        args = func.contract_fn
        contract_address = _format_sc_address(args.contract_address)

        await confirm_address(
            title,
            contract_address,
            br_name="op_auth_contract_address",
        )

        await confirm_text(
            "op_auth_function",
            title,
            args.function_name,
            description=TR.stellar__function,
        )

        for i, arg in enumerate(args.args):
            arg_str = _format_sc_val(arg)
            await confirm_text(
                "op_auth_arg",
                title=f"{TR.stellar__argument} #{i + 1}",
                data=arg_str,
            )

    # Recursively show sub-invocations
    if invocation.sub_invocations:
        await _confirm_nested_invocations(invocation.sub_invocations)


def _format_sc_address(addr: StellarSCAddress) -> str:
    from trezor.enums import StellarSCAddressType

    from .. import helpers

    if addr.type == StellarSCAddressType.SC_ADDRESS_TYPE_ACCOUNT:
        return helpers.address_from_public_key(addr.address)
    elif addr.type == StellarSCAddressType.SC_ADDRESS_TYPE_CONTRACT:
        return helpers.encode_strkey(helpers.STRKEY_CONTRACT, addr.address)
    elif addr.type == StellarSCAddressType.SC_ADDRESS_TYPE_MUXED_ACCOUNT:
        return helpers.encode_strkey(helpers.STRKEY_MUXED_ACCOUNT, addr.address)
    elif addr.type == StellarSCAddressType.SC_ADDRESS_TYPE_CLAIMABLE_BALANCE:
        return helpers.encode_strkey(helpers.STRKEY_CLAIMABLE_BALANCE, addr.address)
    elif addr.type == StellarSCAddressType.SC_ADDRESS_TYPE_LIQUIDITY_POOL:
        return helpers.encode_strkey(helpers.STRKEY_LIQUIDITY_POOL, addr.address)
    else:
        raise ProcessError(f"Stellar: unsupport SCAddress type: {addr.type}")


def _format_sc_val(val: StellarSCVal) -> str:
    """Format SCVal as a human-readable string, using JSON for complex types."""
    from trezor.enums import StellarSCValType

    t = val.type

    if t == StellarSCValType.SCV_BOOL:
        return "true" if val.b else "false"
    elif t == StellarSCValType.SCV_VOID:
        return "void"
    elif t == StellarSCValType.SCV_U32:
        if val.u32 is None:
            raise DataError("Stellar: missing u32 value")
        return str(val.u32)
    elif t == StellarSCValType.SCV_I32:
        if val.i32 is None:
            raise DataError("Stellar: missing i32 value")
        return str(val.i32)
    elif t == StellarSCValType.SCV_U64:
        if val.u64 is None:
            raise DataError("Stellar: missing u64 value")
        return str(val.u64)
    elif t == StellarSCValType.SCV_I64:
        if val.i64 is None:
            raise DataError("Stellar: missing i64 value")
        return str(val.i64)
    elif t == StellarSCValType.SCV_TIMEPOINT:
        if val.timepoint is None:
            raise DataError("Stellar: missing timepoint value")
        return str(val.timepoint)
    elif t == StellarSCValType.SCV_DURATION:
        if val.duration is None:
            raise DataError("Stellar: missing duration value")
        return str(val.duration)
    elif t == StellarSCValType.SCV_U128:
        if val.u128 is None:
            raise DataError("Stellar: missing u128 value")
        return _format_u128(val.u128)
    elif t == StellarSCValType.SCV_I128:
        if val.i128 is None:
            raise DataError("Stellar: missing i128 value")
        return _format_i128(val.i128)
    elif t == StellarSCValType.SCV_U256:
        if val.u256 is None:
            raise DataError("Stellar: missing u256 value")
        return _format_u256(val.u256)
    elif t == StellarSCValType.SCV_I256:
        if val.i256 is None:
            raise DataError("Stellar: missing i256 value")
        return _format_i256(val.i256)
    elif t == StellarSCValType.SCV_BYTES:
        if val.bytes is None:
            raise DataError("Stellar: missing bytes value")
        return hexlify(val.bytes).decode()
    elif t == StellarSCValType.SCV_STRING:
        if val.string is None:
            raise DataError("Stellar: missing string value")
        # Try UTF-8 decode, fallback to hex if invalid
        try:
            return f'"{bytes(val.string).decode()}"'
        except UnicodeDecodeError:
            return hexlify(val.string).decode()
    elif t == StellarSCValType.SCV_SYMBOL:
        if val.symbol is None:
            raise DataError("Stellar: missing symbol value")
        return val.symbol
    elif t == StellarSCValType.SCV_VEC:
        return _format_vec_as_json(val.vec)
    elif t == StellarSCValType.SCV_MAP:
        return _format_map_as_json(val.map)
    elif t == StellarSCValType.SCV_ADDRESS:
        if val.address is None:
            raise DataError("Stellar: missing address value")
        return _format_sc_address(val.address)
    else:
        raise DataError(f"Stellar: unsupported SCVal type {t}")


def _format_vec_as_json(vec: list) -> str:
    """Format a vector as JSON array."""
    items = [_format_sc_val(item) for item in vec]
    return "[" + ", ".join(items) + "]"


def _format_map_as_json(map_entries: list) -> str:
    """Format a map as JSON object."""
    pairs = []
    for entry in map_entries:
        if entry.key is not None and entry.value is not None:
            key = _format_sc_val(entry.key)
            value = _format_sc_val(entry.value)
            pairs.append(f"{key}: {value}")
    return "{" + ", ".join(pairs) + "}"


_MASK64 = 0xFFFFFFFFFFFFFFFF


def _format_u128(parts: "StellarUInt128Parts") -> str:
    value = ((parts.hi & _MASK64) << 64) | (parts.lo & _MASK64)
    return str(value)


def _format_i128(parts: "StellarInt128Parts") -> str:
    value = ((parts.hi & _MASK64) << 64) | (parts.lo & _MASK64)
    if parts.hi < 0:
        value -= 1 << 128
    return str(value)


def _format_u256(parts: "StellarUInt256Parts") -> str:
    value = (
        ((parts.hi_hi & _MASK64) << 192)
        | ((parts.hi_lo & _MASK64) << 128)
        | ((parts.lo_hi & _MASK64) << 64)
        | (parts.lo_lo & _MASK64)
    )
    return str(value)


def _format_i256(parts: "StellarInt256Parts") -> str:
    value = (
        ((parts.hi_hi & _MASK64) << 192)
        | ((parts.hi_lo & _MASK64) << 128)
        | ((parts.lo_hi & _MASK64) << 64)
        | (parts.lo_lo & _MASK64)
    )
    if parts.hi_hi < 0:
        value -= 1 << 256
    return str(value)
