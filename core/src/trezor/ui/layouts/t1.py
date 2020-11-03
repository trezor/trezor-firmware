from micropython import const

from trezor.messages import ButtonRequestType
from trezor.ui.qr import Qr
from trezor.utils import chunks

from .common import interact
from ..components.common import break_path_to_lines
from ..components.common.confirm import CONFIRMED
from ..components.t1.confirm import Confirm
from ..components.t1.text import Text

if False:
    from typing import Iterator, Iterable, LayoutType, Sequence, Union

    from trezor import wire
    from trezor.messages.ButtonRequest import EnumTypeButtonRequestType


def confirm_action(
    ctx: wire.GenericContext,
    br_type: str,
    title: str,
    action: Iterable[str] = None,
    description: Iterable[str] = None,
    verb: Union[str, bytes] = "CONFIRM",
    icon: str = None,
    br_code: EnumTypeButtonRequestType = ButtonRequestType.Other,
    **kwargs,
) -> LayoutType:
    text = Text(title.upper(), new_lines=False)
    if action:
        for line in action:
            text.bold(line)
            text.br()
        if not kwargs.get('compact', False):
            text.br_half()
    if description:
        for line in description:
            text.normal(line)
            text.br()

    confirm = "icon" if isinstance(verb, bytes) else verb  # type: str
    return interact(ctx, Confirm(text, confirm=confirm), br_type, br_code)


def confirm_wipe(ctx: wire.GenericContext) -> LayoutType:
    text = Text()
    text.bold("Do you want to wipe", "the device?")
    text.br_half()
    text.normal("All data will be lost.")
    return interact(
        ctx,
        Confirm(text, confirm="WIPE DEVICE", cancel="CANCEL"),
        "confirm_wipe",
        ButtonRequestType.WipeDevice,
    )


def confirm_reset_device(ctx: wire.GenericContext, prompt: str) -> LayoutType:
    text = Text(new_lines=False)
    for line in prompt:
        text.bold(line)
        text.br()
    text.br_half()
    text.normal("By continuing you agree")
    text.br()
    text.normal("to")
    text.bold("trezor.io/tos")
    return interact(
        ctx,
        Confirm(text, confirm="CREATE", cancel="CANCEL"),
        "confirm_setup",
        ButtonRequestType.ResetDevice,
    )


async def confirm_backup(ctx: wire.GenericContext) -> bool:
    text1 = Text()
    text1.bold("New wallet created", "successfully!")
    text1.br_half()
    text1.normal("You should back up your", "new wallet right now.")

    text2 = Text("Skip the backup?")  # new_lines=False?
    text2.normal("You can back up ", "your Trezor once, ", "at any time.")

    if (
        await interact(
            ctx,
            Confirm(text1, confirm="BACKUP", cancel="NO"),
            "confirm_backup",
            ButtonRequestType.ResetDevice,
        )
        is CONFIRMED
    ):
        return True

    confirmed = (
        await interact(
            ctx,
            Confirm(text2, confirm="BACKUP", cancel="NO"),
            "confirm_backup",
            ButtonRequestType.ResetDevice,
        )
    ) is CONFIRMED
    return confirmed


def confirm_path_warning(ctx: wire.GenericContext, path: str) -> LayoutType:
    text = Text("WRONG ADDRESS PATH")
    text.br_half()
    text.mono(*break_path_to_lines(path, 16))
    text.br_half()
    text.normal("Are you sure?")
    return interact(
        ctx,
        Confirm(text),
        "path_warning",
        ButtonRequestType.UnknownDerivationPath,
    )


def _show_qr(
    address: str,
) -> Confirm:
    QR_X = const(32)
    QR_Y = const(32)
    QR_SIZE_THRESHOLD = const(43)
    QR_COEF = const(2) if len(address) < QR_SIZE_THRESHOLD else const(1)
    qr = Qr(address, QR_X, QR_Y, QR_COEF)

    return Confirm(qr, confirm="CONTINUE", cancel="")


def _split_address(address: str) -> Iterator[str]:
    return chunks(address, 17)  # 18 on T1


def _split_op_return(data: str) -> Iterator[str]:
    if len(data) >= 18 * 5:
        data = data[: (18 * 5 - 3)] + "..."
    return chunks(data, 18)


def _show_address(
    address: str,
    desc: str,
    network: str = None,
) -> Confirm:
    text = Text(desc)
    if network is not None:
        text.normal("%s network" % network)
    text.mono(*_split_address(address))

    return Confirm(text, confirm="CONTINUE", cancel="QR CODE")


def _show_xpub(xpub: str, desc: str, cancel: str) -> Confirm:
    return Confirm(Text("NOT IMPLEMENTED"), cancel=cancel.upper())


async def show_address(
    ctx: wire.GenericContext,
    address: str,
    address_qr: str = None,
    desc: str = "Confirm address",
    network: str = None,
    multisig_index: int = None,
    xpubs: Sequence[str] = [],
) -> None:
    is_multisig = len(xpubs) > 0
    while True:
        if (
            await interact(
                ctx,
                _show_address(address, desc, network),
                "show_address",
            )
            is CONFIRMED
        ):
            break
        if (
            await interact(
                ctx,
                _show_qr(address if address_qr is None else address_qr),
                "show_qr",
            )
            is CONFIRMED
        ):
            break

        if is_multisig:
            for i, xpub in enumerate(xpubs):
                cancel = "NEXT" if i < len(xpubs) - 1 else "ADDRESS"
                desc = "XPUB #%d" % (i + 1)
                desc += " (yours)" if i == multisig_index else " (others)"
                if (
                    await interact(
                        ctx,
                        _show_xpub(xpub, desc=desc, cancel=cancel),
                        "show_xpub",
                        ButtonRequestType.PublicKey,
                    )
                    is CONFIRMED
                ):
                    return


def confirm_output(
    ctx: wire.GenericContext,
    title: str,
    address: str = None,
    amount: str = None,
    data: str = None,
    hex_data: str = None,
) -> LayoutType:
    if address is not None and amount is not None:
        text = Text("TRANSACTION")
        text.normal("Send " + amount + " to")
        text.mono(*_split_address(address))
    elif data is not None:
        text = Text("OMNI TRANSACTION")
        text.normal(data)
    elif hex_data is not None:
        text = Text("OP_RETURN")
        text.mono(*_split_op_return(hex_data))
    else:
        raise ValueError

    return interact(
        ctx, Confirm(text), "confirm_output", ButtonRequestType.ConfirmOutput
    )


def confirm_total(
    ctx: wire.GenericContext, total_amount: str, fee_amount: str
) -> LayoutType:
    text = Text("TRANSACTION")
    text.bold("Total amount:")
    text.mono(total_amount)
    text.bold("Fee included:")
    text.mono(fee_amount)
    return interact(
        ctx,
        Confirm(text, confirm="HOLD TO CONFIRM", cancel="X"),
        "confirm_total",
        ButtonRequestType.SignTx,
    )


def confirm_joint_total(
    ctx: wire.GenericContext, spending_amount: str, total_amount: str
) -> LayoutType:
    text = Text("JOINT TRANSACTION")
    text.bold("You are contributing:")
    text.mono(spending_amount)
    text.bold("to the total amount:")
    text.mono(total_amount)
    return interact(
        ctx,
        Confirm(text, confirm="HOLD TO CONFIRM", cancel="X"),
        "confirm_joint_total",
        ButtonRequestType.SignTx,
    )


def confirm_feeoverthreshold(ctx: wire.GenericContext, fee_amount: str) -> LayoutType:
    text = Text("HIGH FEE")
    text.normal("The fee of")
    text.bold(fee_amount)
    text.normal("is unexpectedly high.", "Continue?")
    return interact(
        ctx,
        Confirm(text),
        "confirm_fee_over_threshold",
        ButtonRequestType.FeeOverThreshold,
    )


def confirm_change_count_over_threshold(
    ctx: wire.GenericContext, change_count: int
) -> LayoutType:
    text = Text("WARNING!")
    text.normal("There are {}".format(change_count))
    text.normal("change-outputs.")
    text.br_half()
    text.normal("Continue?")
    return interact(
        ctx,
        Confirm(text),
        "confirm_change_count_over_threshold",
        ButtonRequestType.SignTx,
    )


def confirm_nondefault_locktime(
    ctx: wire.GenericContext,
    lock_time_disabled: bool = False,
    lock_time_height: int = None,
    lock_time_stamp: int = None,
) -> LayoutType:
    if lock_time_disabled:
        text = Text("WARNING!")
        text.normal("Locktime is set but will", "have no effect.")
        text.br_half()
    else:
        text = Text("CONFIRM LOCKTIME")
        text.normal("Locktime for this", "transaction is set to")
        if lock_time_height is not None:
            text.normal("blockheight:")
            text.bold(lock_time_height)
        elif lock_time_stamp is not None:
            text.normal("timestamp:")
            text.bold(lock_time_stamp)
        else:
            raise ValueError

    text.normal("Continue?")
    return interact(
        ctx, Confirm(text), "confirm_nondefault_locktime", ButtonRequestType.SignTx
    )
