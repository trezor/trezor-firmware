from typing import TYPE_CHECKING
from ubinascii import hexlify

import trezor.ui.layouts as layouts
from trezor import TR, strings, wire
from trezor.enums import ButtonRequestType, StellarSCValType
from trezor.wire import DataError, ProcessError

from apps.common.paths import address_n_to_str

from . import consts
from .helpers import resolve_sep41_token

if TYPE_CHECKING:
    from buffer_types import AnyBytes
    from typing import Iterable

    from trezor.enums import StellarMemoType
    from trezor.messages import (
        PaymentRequest,
        StellarAsset,
        StellarInt128Parts,
        StellarInt256Parts,
        StellarInvokeContractArgs,
        StellarSCVal,
        StellarSCValMapEntry,
        StellarSorobanAuthorizedInvocation,
        StellarUInt128Parts,
        StellarUInt256Parts,
    )
    from trezor.ui.layouts import StrPropertyType

    from apps.common.paths import Bip32Path


async def require_confirm_tx_source(tx_source: str) -> None:
    await layouts.show_warning(
        br_name="confirm_tx_source",
        content=TR.stellar__transaction_source_diff_warning,
        br_code=ButtonRequestType.Warning,
    )

    await layouts.confirm_address(
        title=TR.stellar__transaction_source,
        address=tx_source,
        br_name="confirm_tx_source",
        br_code=ButtonRequestType.ConfirmOutput,
        verb=TR.buttons__continue,
    )


async def require_confirm_memo(memo_type: StellarMemoType, memo_text: str) -> None:
    from trezor.enums import StellarMemoType

    if memo_type == StellarMemoType.TEXT:
        description = "Memo (TEXT)"
    elif memo_type == StellarMemoType.ID:
        description = "Memo (ID)"
    elif memo_type == StellarMemoType.HASH:
        description = "Memo (HASH)"
    elif memo_type == StellarMemoType.RETURN:
        description = "Memo (RETURN)"
    else:
        return await layouts.show_warning(
            br_name="confirm_memo",
            content=TR.stellar__exchanges_require_memo,
        )

    await layouts.confirm_value(
        title=TR.stellar__confirm_memo,
        value=memo_text,
        description=description,
        br_name="confirm_memo",
        br_code=ButtonRequestType.ConfirmOutput,
        verb=TR.buttons__continue,
        is_data=False,
    )


async def require_confirm_payment_request(
    provider_address: str,
    verified_payment_request: PaymentRequest,
    address_n: Bip32Path | None,
    asset: StellarAsset,
) -> None:
    from trezor.ui.layouts import confirm_payment_request
    from trezor.ui.layouts.slip24 import Refund, Trade

    from apps.common.payment_request import parse_amount

    total_amount = format_amount(parse_amount(verified_payment_request), asset)

    texts: list[tuple[str | None, str]] = []
    refunds = []
    trades = []
    for memo in verified_payment_request.memos:
        if memo.text_memo is not None:
            texts.append((None, memo.text_memo.text))
        elif memo.text_details_memo is not None:
            texts.append((memo.text_details_memo.title, memo.text_details_memo.text))
        elif memo.refund_memo:
            refund_account_path = address_n_to_str(memo.refund_memo.address_n)
            refunds.append(Refund(memo.refund_memo.address, None, refund_account_path))
        elif memo.coin_purchase_memo:
            coin_purchase_account_path = address_n_to_str(
                memo.coin_purchase_memo.address_n
            )
            trades.append(
                Trade(
                    f"-\u00a0{total_amount}",
                    f"+\u00a0{memo.coin_purchase_memo.amount}",
                    memo.coin_purchase_memo.address,
                    None,
                    coin_purchase_account_path,
                )
            )
        else:
            raise wire.DataError("Unrecognized memo type in payment request memo.")

    account_path = address_n_to_str(address_n) if address_n else None
    account_items = []
    if account_path:
        account_items.append((TR.address_details__derivation_path, account_path))

    await confirm_payment_request(
        verified_payment_request.recipient_name,
        provider_address,
        texts,
        refunds,
        trades,
        account_items,
        None,
        None,
    )


async def require_confirm_final(
    address_n: list[int],
    fee: int,
    timebounds: tuple[int, int],
    is_sending_from_trezor_account: bool,
) -> None:
    from trezor.wire import DataError

    from apps.common import paths

    from . import PATTERN, SLIP44_ID

    timebounds_start, timebounds_end = timebounds
    extra_items: Iterable[StrPropertyType] = (
        (
            TR.stellar__valid_from,
            (
                strings.format_timestamp(timebounds_start)
                if timebounds_start > 0
                else TR.stellar__no_restriction
            ),
            None,
        ),
        (
            TR.stellar__valid_to,
            (
                strings.format_timestamp(timebounds_end)
                if timebounds_end > 0
                else TR.stellar__no_restriction
            ),
            None,
        ),
    )

    account_name = paths.get_account_name("Stellar", address_n, PATTERN, SLIP44_ID)
    account_path = paths.address_n_to_str(address_n)

    if account_name is None:
        raise DataError("Stellar: Invalid account name")

    await layouts.confirm_stellar_tx(
        format_amount(fee),
        account_name,
        account_path,
        is_sending_from_trezor_account,
        extra_items,
    )


async def require_confirm_auth_signing_address(
    address: str, address_n: Bip32Path
) -> None:
    """Confirm the device account whose key signs the Soroban authorization.

    Always the first screen of the flow, like the signing address screen of
    Ethereum's message signing flows.
    """
    from apps.common import paths

    from . import PATTERN, SLIP44_ID

    account_name = paths.get_account_name("Stellar", address_n, PATTERN, SLIP44_ID)
    account_path = paths.address_n_to_str(address_n)

    if account_name is None:
        raise wire.DataError("Stellar: Invalid account name")

    info_items: list[StrPropertyType] = [
        (TR.words__account, account_name, None),
        (TR.address_details__derivation_path, account_path, None),
    ]

    await layouts.confirm_address(
        title=TR.sign_message__confirm_address,
        address=address,
        br_name="confirm_auth_signing_address",
        br_code=ButtonRequestType.ConfirmOutput,
        verb=TR.buttons__continue,
        info_items=info_items,
        info_title=TR.address_details__account_info,
    )


async def require_confirm_auth_on_behalf_of(address: str) -> None:
    """Confirm the address whose Soroban authorization credentials are signed.

    Only shown when it differs from the signing address, i.e. when the device
    account signs on behalf of another party. e.g. a contract account of
    which the device account is a signer.
    """
    await layouts.confirm_address(
        title=TR.words__authorization,
        address=address,
        description=TR.stellar__on_behalf_of,
        br_name="confirm_auth_on_behalf_of",
        br_code=ButtonRequestType.ConfirmOutput,
        verb=TR.buttons__continue,
    )


async def require_confirm_signature_expiration_ledger(
    signature_expiration_ledger: int,
) -> None:
    await layouts.confirm_value(
        title=TR.stellar__sign_authorization,
        value=str(signature_expiration_ledger),
        description=TR.stellar__valid_until_ledger,
        br_name="confirm_soroban_auth",
        br_code=ButtonRequestType.SignTx,
        hold=True,
        is_data=False,
    )


async def confirm_invoke_contract_args(
    args: StellarInvokeContractArgs,
    is_transaction_host_function: bool,
    title: str | None = None,
) -> None:
    """Confirm a contract call using the generic, unparsed arguments UI.

    `is_transaction_host_function` is True for the function invoked directly
    by a transaction and False for a node of an authorization tree. Tree nodes
    must provide `title`; it identifies their position while each screen's
    usual title moves into its description or subtitle.
    """
    authorization_title: str | None = None
    if not is_transaction_host_function:
        assert title is not None
        authorization_title = title

    await layouts.confirm_address(
        authorization_title or TR.stellar__invoke_contract,
        args.contract_address,
        description=(
            None if is_transaction_host_function else TR.stellar__invoke_contract
        ),
        br_name="op_invoke_contract_address",
    )
    await layouts.confirm_text(
        "op_invoke_function",
        authorization_title or TR.words__function,
        args.function_name,
        description=None if is_transaction_host_function else TR.words__function,
    )
    if not args.args:
        return
    props = [
        (f"{i + 1} / {len(args.args)}", _format_sc_val(arg), True)
        for i, arg in enumerate(args.args)
    ]
    await layouts.confirm_properties(
        "op_invoke_args",
        authorization_title or TR.words__arguments,
        props,
        None if is_transaction_host_function else TR.words__arguments,
    )


# SEP-41 token functions given a dedicated UI, see
# https://github.com/stellar/stellar-protocol/blob/master/ecosystem/sep-0041.md
_SEP41_TRANSFER = "transfer"
_SEP41_APPROVE = "approve"


def parse_sep41_transfer(
    args: StellarInvokeContractArgs,
) -> tuple[str, str, int] | None:
    """Read a SEP-41 `transfer(from, to, amount)` call, or None if it is not one."""
    if args.function_name != _SEP41_TRANSFER or len(args.args) != 3:
        return None
    from_address = _sc_address(args.args[0])
    to_address = _sc_address(args.args[1])
    amount = _sc_amount(args.args[2])
    if from_address is None or to_address is None or amount is None:
        return None
    return from_address, to_address, amount


def parse_sep41_approve(
    args: StellarInvokeContractArgs,
) -> tuple[str, str, int, int] | None:
    """Read a SEP-41 `approve(from, spender, amount, live_until_ledger)` call."""
    if args.function_name != _SEP41_APPROVE or len(args.args) != 4:
        return None
    from_address = _sc_address(args.args[0])
    spender = _sc_address(args.args[1])
    amount = _sc_amount(args.args[2])
    live_until_ledger = _sc_u32(args.args[3])
    if (
        from_address is None
        or spender is None
        or amount is None
        or live_until_ledger is None
    ):
        return None
    return from_address, spender, amount, live_until_ledger


def _sc_address(val: StellarSCVal) -> str | None:
    if val.type != StellarSCValType.SCV_ADDRESS:
        return None
    return val.address


def _sc_amount(val: StellarSCVal) -> int | None:
    """Read an amount suitable for the dedicated token UI.

    Stellar Asset Contracts reject negative amounts. Custom SEP-41 contracts
    may accept them, but we deliberately leave such calls to the raw contract
    flow instead of presenting them as regular token operations.
    """
    if val.type != StellarSCValType.SCV_I128 or val.i128 is None:
        return None
    amount = _i128_value(val.i128)
    if amount < 0:
        return None
    return amount


def _sc_u32(val: StellarSCVal) -> int | None:
    if val.type != StellarSCValType.SCV_U32:
        return None
    return val.u32


def _sep41_approve_action(amount: int) -> str:
    """Approve action label: an allowance of zero revokes it."""
    return TR.stellar__revoke_approval if amount == 0 else TR.stellar__approve_token


def _should_show_from_address(
    from_address: str, authorizing_address: str | None
) -> bool:
    """Show `from` unless the same address already authorizes the whole tree."""
    return authorizing_address is None or from_address != authorizing_address


async def confirm_invoke_contract(
    args: StellarInvokeContractArgs,
    network_id: AnyBytes,
    authorizing_address: str | None,
    is_transaction_host_function: bool,
    title: str | None = None,
) -> None:
    """Confirm a contract call, using the dedicated token UI when possible.

    `is_transaction_host_function` explicitly distinguishes the two callers:

    - True: the host function invoked directly by a transaction. Transfers
      retain the standard payment-style output screen and `title` is omitted.
    - False: an invocation displayed from an authorization tree, whether the
      tree is embedded in a transaction or signed standalone. `title` is
      required and identifies the node; the token action becomes its subtitle.

    `authorizing_address` is used in both contexts to avoid repeating the
    address that already authorizes the transaction operation or the whole
    authorization tree.
    """
    asset = resolve_sep41_token(args, network_id)
    if asset is not None:
        if await _confirm_sep41_token(
            args,
            asset,
            authorizing_address,
            is_transaction_host_function,
            title,
        ):
            return

    await confirm_invoke_contract_args(args, is_transaction_host_function, title)


async def _confirm_sep41_token(
    args: StellarInvokeContractArgs,
    asset: StellarAsset,
    authorizing_address: str | None,
    is_transaction_host_function: bool,
    title: str | None,
) -> bool:
    """Confirm a supported SEP-41 call as a token operation.

    The calling contexts determine `is_transaction_host_function` and `title`:

    - A host function invoked directly by a transaction uses True and `None`.
      The token action itself is the screen title: "Send", "Approve token", or
      "Revoke approval" for an approval amount of zero.
    - An authorization-tree node embedded in a transaction uses False and a
      positional title such as "Authorization #1" or "Authorization #1.1".
    - A standalone authorization-entry node uses False and a title such as
      "Authorization" or "Authorization .1".

    For authorization-tree nodes, the title identifies the node while the
    token action ("Transfer token", "Approve token", or "Revoke approval") is
    shown as its subtitle.

    Anything but a well-formed `transfer` or `approve` is left to the generic
    contract flow (returns False).
    """
    if is_transaction_host_function:
        assert title is None
        authorization_title = None
    else:
        assert title is not None
        authorization_title = title

    transfer = parse_sep41_transfer(args)
    if transfer is not None:
        from_address, to_address, amount = transfer
        # The transaction root shows a transfer as "Send": it is the
        # transaction's own action, framed like a classic payment. A tree
        # node instead describes what a signature permits, an entry may
        # belong to another party altogether, so it gets a neutral,
        # perspective-free label, in line with "Approve token".
        action = (
            TR.words__send
            if is_transaction_host_function
            else TR.stellar__transfer_token
        )
        screen_title = authorization_title or action
        # Direct transaction: "Send" is the title, while
        # `confirm_stellar_output` supplies the recipient context.
        # Authorization tree: "Authorization #..." is the title and
        # "Transfer token" is the subtitle.
        subtitle = "" if is_transaction_host_function else action
        if _should_show_from_address(from_address, authorizing_address):
            await layouts.confirm_stellar_address(
                screen_title,
                subtitle,
                from_address,
                TR.stellar__from,
                "op_invoke_from",
            )

        if not is_transaction_host_function:
            await layouts.confirm_stellar_address(
                screen_title,
                subtitle,
                to_address,
                TR.stellar__to,
                "op_invoke_to",
            )
            await layouts.confirm_stellar_output_amount(
                screen_title,
                subtitle,
                format_amount(amount, asset),
                asset,
                TR.words__amount,
                token_contract=args.contract_address,
            )
        else:
            await layouts.confirm_stellar_output(
                to_address,
                format_amount(amount, asset),
                output_index=0,  # a Soroban operation is always the only one
                asset=asset,
                token_contract=args.contract_address,
            )
        return True

    approve = parse_sep41_approve(args)
    if approve is not None:
        from_address, spender, amount, live_until_ledger = approve
        action = _sep41_approve_action(amount)
        screen_title = authorization_title or action
        subtitle = "" if is_transaction_host_function else action
        if _should_show_from_address(from_address, authorizing_address):
            await layouts.confirm_stellar_address(
                screen_title,
                subtitle,
                from_address,
                TR.stellar__from,
                "op_invoke_from",
            )
        await layouts.confirm_stellar_address(
            screen_title,
            subtitle,
            spender,
            TR.stellar__spender,
            "op_invoke_spender",
        )
        if amount == 0:
            # "Revoke approval" already communicates the zero allowance, so
            # identify the token instead of displaying the omitted amount.
            display_value = format_asset(asset)
            value_label = TR.words__token
        else:
            display_value = format_amount(amount, asset)
            value_label = TR.words__amount
        await layouts.confirm_stellar_output_amount(
            screen_title,
            subtitle,
            display_value,
            asset,
            value_label,
            token_contract=args.contract_address,
        )
        await layouts.confirm_stellar_valid_until(
            screen_title,
            subtitle,
            live_until_ledger,
            "op_invoke_valid_until",
        )
        return True

    return False


async def confirm_authorized_invocation(
    invocation: StellarSorobanAuthorizedInvocation,
    network_id: AnyBytes,
    authorizing_address: str,
) -> None:
    """Confirm a standalone authorized invocation tree (auth entry signing).

    Unlike in a transaction, there is always exactly one entry being signed, so
    its root label is empty; sub-invocations are numbered relative to it
    (".1", ".1.2", ...), the same paths they would have inside a transaction.
    """
    await confirm_invocation(invocation, "", network_id, authorizing_address)


async def confirm_invocation(
    invocation: StellarSorobanAuthorizedInvocation,
    position: str,
    network_id: AnyBytes,
    authorizing_address: str | None,
    is_root: bool = False,
) -> None:
    """Confirm an authorized invocation and its sub-invocations recursively.

    The whole authorization tree is shown by default (it is security-critical and
    can differ from the host function being invoked). `position` is the root
    label plus the dot-delimited path in the auth tree (e.g. "#2", "#2.1" in a
    transaction), or empty for the unlabeled root of a standalone authorization
    entry (whose children are then ".1", ".1.2", ...), so a given entry's
    children carry the same paths in both flows. `authorizing_address` belongs
    to the whole tree and is propagated unchanged to every child.
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
        await confirm_invoke_contract(
            func.contract_fn,
            network_id,
            authorizing_address,
            is_transaction_host_function=False,
            title=title,
        )

    for i, sub in enumerate(invocation.sub_invocations):
        await confirm_invocation(
            sub, f"{position}.{i + 1}", network_id, authorizing_address
        )


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
        except OverflowError:
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


def _i128_value(parts: StellarInt128Parts) -> int:
    value = ((parts.hi & _MASK64) << 64) | (parts.lo & _MASK64)
    if parts.hi < 0:
        value -= 1 << 128
    return value


def _format_i128(parts: StellarInt128Parts) -> str:
    return str(_i128_value(parts))


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


def format_asset(asset: StellarAsset | None) -> str:
    from trezor.enums import StellarAssetType
    from trezor.wire import DataError

    if asset is None or asset.type == StellarAssetType.NATIVE:
        return "XLM"
    else:
        if asset.code is None:
            raise DataError("Stellar asset code is missing")
        return asset.code


def format_amount(amount: int, asset: StellarAsset | None = None) -> str:
    return (
        strings.format_amount(amount, consts.AMOUNT_DECIMALS)
        + " "
        + format_asset(asset)
    )
