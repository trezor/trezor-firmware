from typing import TYPE_CHECKING
from ubinascii import hexlify

from trezor import TR
from trezor.enums import StellarSCValType
from trezor.ui.layouts import (
    confirm_address,
    confirm_properties,
    confirm_stellar_output,
    confirm_stellar_output_amount,
    confirm_text,
    confirm_value,
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
        StellarHostFunction,
        StellarInt128Parts,
        StellarInt256Parts,
        StellarInvokeContractArgs,
        StellarInvokeHostFunctionOp,
        StellarManageBuyOfferOp,
        StellarManageDataOp,
        StellarManageSellOfferOp,
        StellarPathPaymentStrictReceiveOp,
        StellarPathPaymentStrictSendOp,
        StellarPaymentOp,
        StellarSCVal,
        StellarSCValMapEntry,
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
        format_amount(op.limit, op.asset),
        description=TR.stellar__limit,
        br_name="op_change_trust",
        is_data=False,
        verb=TR.buttons__continue,
    )

    await confirm_asset_issuer(op.asset)


async def confirm_create_account_op(
    op: StellarCreateAccountOp, output_index: int
) -> None:
    from trezor.enums import StellarAssetType
    from trezor.messages import StellarAsset

    await confirm_stellar_output(
        op.new_account,
        format_amount(op.starting_balance),
        output_index=output_index,
        asset=StellarAsset(type=StellarAssetType.NATIVE),
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
            verb=TR.buttons__continue,
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
    await confirm_stellar_output(
        op.destination_account,
        format_amount(op.destination_amount, op.destination_asset),
        output_index,
        op.destination_asset,
        address_description=TR.stellar__path_pay,
        amount_description=TR.stellar__path_pay,
    )

    await confirm_stellar_output_amount(
        TR.stellar__debited_amount,
        f"{TR.words__recipient} #{output_index + 1}",
        format_amount(op.send_max, op.send_asset),
        op.send_asset,
        TR.stellar__pay_at_most,
    )


async def confirm_path_payment_strict_send_op(
    op: StellarPathPaymentStrictSendOp,
    output_index: int,
) -> None:
    await confirm_stellar_output(
        op.destination_account,
        format_amount(op.destination_min, op.destination_asset),
        output_index,
        op.destination_asset,
        address_description=TR.stellar__path_pay_at_least,
        amount_description=TR.stellar__path_pay_at_least,
    )

    await confirm_stellar_output_amount(
        TR.stellar__debited_amount,
        f"{TR.words__recipient} #{output_index + 1}",
        format_amount(op.send_amount, op.send_asset),
        op.send_asset,
        TR.stellar__pay,
    )


async def confirm_payment_op(op: StellarPaymentOp, output_index: int) -> None:
    await confirm_stellar_output(
        op.destination_account,
        format_amount(op.amount, op.asset),
        output_index,
        op.asset,
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
    balance_id = hexlify(op.balance_id).decode()
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


async def _confirm_invoke_contract_args(
    args: StellarInvokeContractArgs,
    br_name_prefix: str,
    title: str | None = None,
) -> None:
    # If title is not empty, it is shared across screens;
    # the per-screen label moves into the description / subtitle.
    await confirm_address(
        title or TR.stellar__invoke_contract,
        args.contract_address,
        description=TR.stellar__invoke_contract if title else None,
        br_name=f"{br_name_prefix}_contract_address",
    )
    await confirm_text(
        f"{br_name_prefix}_function",
        title or TR.words__function,
        args.function_name,
        description=TR.words__function if title else None,
    )
    if not args.args:
        return
    props = [
        (f"{i + 1} / {len(args.args)}", _format_sc_val(arg), True)
        for i, arg in enumerate(args.args)
    ]
    await confirm_properties(
        f"{br_name_prefix}_args",
        title or TR.words__arguments,
        props,
        TR.words__arguments if title else None,
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


async def confirm_invoke_host_function_op(op: StellarInvokeHostFunctionOp) -> None:
    from trezor.enums import StellarHostFunctionType, StellarSorobanCredentialsType
    from trezor.ui.layouts import should_show_more

    function = op.function

    if function.type == StellarHostFunctionType.HOST_FUNCTION_TYPE_INVOKE_CONTRACT:
        if function.invoke_contract is None:
            raise DataError("Stellar: missing invoke_contract")

        await _confirm_invoke_contract_args(
            function.invoke_contract,
            br_name_prefix="op_invoke",
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
                auth_entry, shown, _is_root_auth_entry(auth_entry, function)
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
                auth_entry, shown, _is_root_auth_entry(auth_entry, function)
            )


async def _confirm_auth_entry(
    auth: StellarSorobanAuthorizationEntry, position: int, is_root: bool = False
) -> None:
    from trezor.enums import StellarSorobanCredentialsType

    creds = auth.credentials

    if creds.type == StellarSorobanCredentialsType.SOROBAN_CREDENTIALS_ADDRESS_V2:
        if creds.address_v2 is None:
            raise DataError("Stellar: missing address_v2 credentials")

        await confirm_address(
            f"{TR.words__authorization} #{position}",
            creds.address_v2.address,
            description=TR.words__address,
            br_name="op_auth_entry_address",
        )

    # Show the whole authorized invocation tree starting from its root (not just the
    # nested sub-invocations), so the user sees exactly what this signature authorizes.
    await _confirm_invocation(auth.root_invocation, f"#{position}", is_root=is_root)


async def confirm_authorized_invocation(
    invocation: StellarSorobanAuthorizedInvocation,
) -> None:
    """Confirm a standalone authorized invocation tree (auth entry signing).

    Unlike in a transaction, there is always exactly one entry being signed, so
    its root label is empty; sub-invocations are numbered relative to it
    (".1", ".1.2", ...), the same paths they would have inside a transaction.
    """
    await _confirm_invocation(invocation, "")


async def _confirm_invocation(
    invocation: StellarSorobanAuthorizedInvocation, position: str, is_root: bool = False
) -> None:
    """Confirm an authorized invocation and its sub-invocations recursively.

    The whole authorization tree is shown by default (it is security-critical and
    can differ from the host function being invoked). `position` is the root
    label plus the dot-delimited path in the auth tree (e.g. "#2", "#2.1" in a
    transaction), or empty for the unlabeled root of a standalone authorization
    entry (whose children are then ".1", ".1.2", ...), so a given entry's
    children carry the same paths in both flows.
    """
    from trezor.enums import StellarSorobanAuthorizedFunctionType

    func = invocation.function
    if (
        func.type
        != StellarSorobanAuthorizedFunctionType.SOROBAN_AUTHORIZED_FUNCTION_TYPE_CONTRACT_FN
    ):
        raise ProcessError("Stellar: unsupported authorized function type")
    if func.contract_fn is None:
        raise DataError("Stellar: missing contract_fn")

    if position:
        title = f"{TR.words__authorization} {position}"
    else:
        title = TR.words__authorization

    if not is_root:
        await _confirm_invoke_contract_args(
            func.contract_fn,
            br_name_prefix="op_auth",
            title=title,
        )

    for i, sub in enumerate(invocation.sub_invocations):
        await _confirm_invocation(sub, f"{position}.{i + 1}")


def _escape_str(s: str) -> str:
    # Escape `\` first, then `"`, so an embedded quote cannot close the surrounding
    # string delimiters -- otherwise a string could forge extra vec/map items.
    return s.replace("\\", "\\\\").replace('"', '\\"')


def _format_sc_val(val: StellarSCVal) -> str:
    """Format SCVal as a human-readable string, using JSON for complex types."""
    from trezor.strings import format_duration, format_timestamp

    t = val.type

    if t == StellarSCValType.SCV_BOOL:
        if val.b is None:
            raise DataError("Stellar: missing bool value")
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
        try:
            return format_timestamp(val.timepoint)
        except Exception:
            return str(val.timepoint)
    elif t == StellarSCValType.SCV_DURATION:
        if val.duration is None:
            raise DataError("Stellar: missing duration value")
        return format_duration(val.duration)
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
        return "0x" + hexlify(val.bytes).decode()
    elif t == StellarSCValType.SCV_STRING:
        if val.string is None:
            raise DataError("Stellar: missing string value")
        # Render decoded text as a quoted, escaped string so its content can never
        # forge the surrounding quotes (and thus the vec/map separators). Non-UTF-8
        # bytes can't be shown as text, so render them as hex like SCV_BYTES.
        try:
            return f'"{_escape_str(bytes(val.string).decode())}"'
        except UnicodeError:
            return "0x" + hexlify(val.string).decode()
    elif t == StellarSCValType.SCV_SYMBOL:
        if val.symbol is None:
            raise DataError("Stellar: missing symbol value")
        # Quote and escape like SCV_STRING so the symbol's content can never forge the
        # surrounding vec/map delimiters. A symbol is already a valid UTF-8 str, so no
        # hex fallback is needed (unlike SCV_STRING, which holds raw bytes).
        return f'"{_escape_str(val.symbol)}"'
    elif t == StellarSCValType.SCV_VEC:
        return _format_vec_as_json(val.vec)
    elif t == StellarSCValType.SCV_MAP:
        return _format_map_as_json(val.map)
    elif t == StellarSCValType.SCV_ADDRESS:
        if val.address is None:
            raise DataError("Stellar: missing address value")
        return val.address
    else:
        raise DataError(f"Stellar: unsupported SCVal type {t}")


def _format_vec_as_json(vec: list[StellarSCVal]) -> str:
    """Format a vector as JSON array."""
    items = [_format_sc_val(item) for item in vec]
    return "[" + ", ".join(items) + "]"


def _format_map_as_json(map_entries: list[StellarSCValMapEntry]) -> str:
    """Format a map as JSON object."""
    pairs = []
    for entry in map_entries:
        key = _format_sc_val(entry.key)
        value = _format_sc_val(entry.value)
        pairs.append(f"{key}: {value}")
    return "{" + ", ".join(pairs) + "}"


_MASK64 = 0xFFFF_FFFF_FFFF_FFFF


def _format_u128(parts: StellarUInt128Parts) -> str:
    value = ((parts.hi & _MASK64) << 64) | (parts.lo & _MASK64)
    return str(value)


def _format_i128(parts: StellarInt128Parts) -> str:
    value = ((parts.hi & _MASK64) << 64) | (parts.lo & _MASK64)
    if parts.hi < 0:
        value -= 1 << 128
    return str(value)


def _format_u256(parts: StellarUInt256Parts) -> str:
    value = (
        ((parts.hi_hi & _MASK64) << 192)
        | ((parts.hi_lo & _MASK64) << 128)
        | ((parts.lo_hi & _MASK64) << 64)
        | (parts.lo_lo & _MASK64)
    )
    return str(value)


def _format_i256(parts: StellarInt256Parts) -> str:
    value = (
        ((parts.hi_hi & _MASK64) << 192)
        | ((parts.hi_lo & _MASK64) << 128)
        | ((parts.lo_hi & _MASK64) << 64)
        | (parts.lo_lo & _MASK64)
    )
    if parts.hi_hi < 0:
        value -= 1 << 256
    return str(value)
