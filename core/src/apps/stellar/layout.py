from typing import TYPE_CHECKING

import trezor.ui.layouts as layouts
from trezor import strings, ui
from trezor.enums import (
    ButtonRequestType,
    StellarSCValType,
    StellarSorobanAuthorizedFunctionType,
)
from trezor.ui.layouts import confirm_blob, should_show_more
from trezor.wire import DataError

from . import consts, helpers

if TYPE_CHECKING:
    from trezor.enums import StellarMemoType
    from trezor.messages import (
        StellarAsset,
        StellarInvokeContractArgs,
        StellarSCVal,
        StellarSorobanAuthorizedFunction,
        StellarSorobanAuthorizedInvocation,
    )


async def require_confirm_init(
    address: str,
    network_passphrase: str,
    accounts_match: bool,
) -> None:
    description = "Initialize signing with" + (
        " your account" if accounts_match else ""
    )
    await layouts.confirm_address(
        "Confirm Stellar",
        address,
        description,
        "confirm_init",
    )

    # get_network_warning
    if network_passphrase == consts.NETWORK_PASSPHRASE_PUBLIC:
        network = None
    elif network_passphrase == consts.NETWORK_PASSPHRASE_TESTNET:
        network = "testnet network"
    else:
        network = "private network"

    if network:
        await layouts.confirm_metadata(
            "confirm_init_network",
            "Confirm network",
            "Transaction is on {}",
            network,
            ButtonRequestType.ConfirmOutput,
        )


async def require_confirm_timebounds(start: int, end: int) -> None:
    await layouts.confirm_properties(
        "confirm_timebounds",
        "Confirm timebounds",
        (
            (
                "Valid from (UTC)",
                strings.format_timestamp(start) if start > 0 else "[no restriction]",
            ),
            (
                "Valid to (UTC)",
                strings.format_timestamp(end) if end > 0 else "[no restriction]",
            ),
        ),
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
        return await layouts.confirm_action(
            "confirm_memo",
            "Confirm memo",
            "No memo set!",
            "Important: Many exchanges require a memo when depositing",
            br_code=ButtonRequestType.ConfirmOutput,
        )

    await layouts.confirm_blob(
        "confirm_memo",
        "Confirm memo",
        memo_text,
        description,
    )


async def require_confirm_final(fee: int, num_operations: int) -> None:
    op_str = strings.format_plural("{count} {plural}", num_operations, "operation")
    await layouts.confirm_metadata(
        "confirm_final",
        "Final confirm",
        "Sign this transaction made up of " + op_str + " and pay {}\nfor fee?",
        format_amount(fee),
        hold=True,
    )


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


async def confirm_sc_val(
    parent_objects: list[str],
    val: StellarSCVal,
) -> None:
    import ustruct

    br_type = "confirm_sc_val"
    title = limit_str(".".join(parent_objects))

    async def confirm_value(val: str, val_type: str) -> None:
        await layouts.confirm_value(title, val, val_type, br_type)

    if val.type == StellarSCValType.SCV_BOOL:
        await confirm_value("true" if val.b else "false", "bool")
    elif val.type == StellarSCValType.SCV_VOID:
        await confirm_value("[no content]", "void")
    # SCV_ERROR NOT SUPPORTED
    elif val.type == StellarSCValType.SCV_U32:
        assert val.u32 is not None
        await confirm_value(strings.format_amount(val.u32, 0), "u32")
    elif val.type == StellarSCValType.SCV_I32:
        assert val.i32 is not None
        await confirm_value(strings.format_amount(val.i32, 0), "i32")
    elif val.type == StellarSCValType.SCV_U64:
        assert val.u64 is not None
        await confirm_value(strings.format_amount(val.u64, 0), "u64")
    elif val.type == StellarSCValType.SCV_I64:
        assert val.i64 is not None
        await confirm_value(strings.format_amount(val.i64, 0), "i64")
    elif val.type == StellarSCValType.SCV_TIMEPOINT:
        assert val.timepoint is not None
        await confirm_value(strings.format_timestamp(val.timepoint), "timepoint")
    elif val.type == StellarSCValType.SCV_DURATION:
        assert val.duration is not None
        await confirm_value(strings.format_duration_ms(val.duration * 1000), "duration")
    elif val.type == StellarSCValType.SCV_U128:
        assert val.u128
        value_bytes = ustruct.pack(">QQ", val.u128.hi, val.u128.lo)
        v = helpers.bytes_to_int(value_bytes)
        await confirm_value(strings.format_amount(v, 0), "u128")
    elif val.type == StellarSCValType.SCV_I128:
        assert val.i128
        value_bytes = ustruct.pack(">qQ", val.i128.hi, val.i128.lo)
        v = helpers.bytes_to_int(value_bytes, True)
        await confirm_value(strings.format_amount(v, 0), "i128")
    elif val.type == StellarSCValType.SCV_U256:
        assert val.u256
        value_bytes = ustruct.pack(
            ">QQQQ", val.u256.hi_hi, val.u256.hi_lo, val.u256.lo_hi, val.u256.lo_lo
        )
        v = helpers.bytes_to_int(value_bytes)
        await confirm_value(strings.format_amount(v, 0), "u256")
    elif val.type == StellarSCValType.SCV_I256:
        assert val.i256
        value_bytes = ustruct.pack(
            ">qQQQ", val.i256.hi_hi, val.i256.hi_lo, val.i256.lo_hi, val.i256.lo_lo
        )
        v = helpers.bytes_to_int(value_bytes, True)
        await confirm_value(strings.format_amount(v, 0), "i256")
    elif val.type == StellarSCValType.SCV_BYTES:
        assert val.bytes is not None
        await confirm_blob("confirm_sc_val", title, val.bytes, "bytes")
    elif val.type == StellarSCValType.SCV_STRING:
        assert val.string is not None
        await confirm_value(val.string, "string")
    elif val.type == StellarSCValType.SCV_SYMBOL:
        assert val.symbol is not None
        await confirm_value(val.symbol, "symbol")
    elif val.type == StellarSCValType.SCV_VEC:
        if await should_show_more(
            title,
            ((ui.NORMAL, f"{title} contains {len(val.vec)} elements"),),
            "Show full vec",
            "should_show_vec",
        ):
            for idx, item in enumerate(val.vec):
                await confirm_sc_val(parent_objects + [str(idx)], item)
    elif val.type == StellarSCValType.SCV_MAP:
        if await should_show_more(
            title,
            ((ui.NORMAL, f"{title} contains {len(val.map)} items"),),
            "Show full map",
            "should_show_map",
        ):
            for idx, item in enumerate(val.map):
                assert item.key
                assert item.value
                await confirm_sc_val(parent_objects + [str(idx), "key"], item.key)
                await confirm_sc_val(parent_objects + [str(idx), "value"], item.value)
    elif val.type == StellarSCValType.SCV_ADDRESS:
        assert val.address
        await layouts.confirm_address(title, val.address.address, "address", br_type)
    # SCV_CONTRACT_INSTANCE NOT SUPPORTED
    # SCV_LEDGER_KEY_CONTRACT_INSTANCE NOT SUPPORTED
    # SCV_LEDGER_KEY_NONCE NOT SUPPORTED
    else:
        raise DataError(f"Stellar: Unsupported SCV type: {val.type}")


async def confirm_invoke_contract_args(
    parent_objects: list[str], invoke_contract_args: StellarInvokeContractArgs
):
    title = limit_str(".".join(parent_objects))
    await layouts.confirm_properties(
        "confirm_invoke_contract_args",
        title,
        (
            (
                "Contract Address",
                invoke_contract_args.contract_address.address,
            ),
            ("Function", invoke_contract_args.function_name),
        ),
    )

    # confirm args
    for idx, arg in enumerate(invoke_contract_args.args):
        await confirm_sc_val(parent_objects + ["args", str(idx)], arg)


async def confirm_soroban_authorized_function(
    parent_objects: list[str], func: StellarSorobanAuthorizedFunction
):
    if (
        func.type
        != StellarSorobanAuthorizedFunctionType.SOROBAN_AUTHORIZED_FUNCTION_TYPE_CONTRACT_FN
    ):
        raise DataError(f"Stellar: unsupported function type: {func.type}")
    assert func.contract_fn
    await confirm_invoke_contract_args(parent_objects, func.contract_fn)


async def confirm_soroban_authorized_invocation(
    parent_objects: list[str],
    invocation: StellarSorobanAuthorizedInvocation,
) -> None:
    # TODO: remove comment; common confirm
    # confirm contract function
    await confirm_soroban_authorized_function(parent_objects, invocation.function)

    title = limit_str(".".join(parent_objects))

    # confirm sub_invocations
    if len(invocation.sub_invocations) and await should_show_more(
        title,
        (
            (
                ui.NORMAL,
                f"{title} contains {len(invocation.sub_invocations)} sub invocations",
            ),
        ),
        "Show Sub Invocations",
        "should_show_sub_invocations",
    ):
        for idx, sub_invocation in enumerate(invocation.sub_invocations):
            await confirm_soroban_authorized_invocation(
                parent_objects + ["subs", str(idx)],
                sub_invocation,
            )


async def confirm_soroban_auth_info(
    nonce: int,
    signature_expiration_ledger: int,
    invocation: StellarSorobanAuthorizedInvocation,
) -> None:
    await layouts.confirm_properties(
        "confirm_soroban_auth_info",
        "Confirm Soroban Auth",
        (
            ("Nonce", str(nonce)),
            (
                "Signature Exp Ledger",
                strings.format_amount(signature_expiration_ledger, 0),
            ),
        ),
    )
    await confirm_soroban_authorized_invocation(["root"], invocation)


async def confirm_soroban_auth_final() -> None:
    from trezor.ui.layouts import confirm_action

    await confirm_action(
        "confirm_soroban_auth_final",
        "Confirm Soroban Auth",
        "Really sign Soroban Auth?",
        verb="Hold to confirm",
        hold=True,
    )


def limit_str(s: str, limit: int = 16) -> str:
    """Shortens string to show the last <limit> characters."""
    if len(s) <= limit + 2:
        return s

    return ".." + s[-limit:]
