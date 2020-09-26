from micropython import const

from trezor import ui
from trezor.messages import BackupType
from trezor.ui.container import Container
from trezor.ui.loader import LoaderDanger
from trezor.ui.qr import Qr
from trezor.utils import chunks

from .button import ButtonCancel, ButtonDefault
from .confirm import Confirm, HoldToConfirm
from .text import Text

if False:
    from typing import Iterator
    from ..common import ListsArg


def confirm_ping() -> Confirm:
    text = Text("Confirm")
    return Confirm(text)


def confirm_reset_device(backup_type: str) -> Confirm:
    text = Text("Create new wallet", ui.ICON_RESET, new_lines=False)
    if backup_type == str(BackupType.Slip39_Basic):
        text.bold("Create a new wallet")
        text.br()
        text.bold("with Shamir Backup?")
    elif backup_type == str(BackupType.Slip39_Advanced):
        text.bold("Create a new wallet")
        text.br()
        text.bold("with Super Shamir?")
    else:
        text.bold("Do you want to create")
        text.br()
        text.bold("a new wallet?")
    text.br()
    text.br_half()
    text.normal("By continuing you agree")
    text.br()
    text.normal("to")
    text.bold("https://trezor.io/tos")
    return Confirm(text, major_confirm=True)


def confirm_backup1() -> Confirm:
    text = Text("Success", ui.ICON_CONFIRM, ui.GREEN, new_lines=False)
    text.bold("New wallet created")
    text.br()
    text.bold("successfully!")
    text.br()
    text.br_half()
    text.normal("You should back up your")
    text.br()
    text.normal("new wallet right now.")
    return Confirm(text, cancel="Skip", confirm="Back up", major_confirm=True)


def confirm_backup2() -> Confirm:
    text = Text("Warning", ui.ICON_WRONG, ui.RED, new_lines=False)
    text.bold("Are you sure you want")
    text.br()
    text.bold("to skip the backup?")
    text.br()
    text.br_half()
    text.normal("You can back up your")
    text.br()
    text.normal("Trezor once, at any time.")
    return Confirm(text, cancel="Skip", confirm="Back up", major_confirm=True)


def confirm_path_warning(_lists: ListsArg) -> Confirm:
    path_lines = _lists["path_lines"]
    assert type(path_lines) == list
    text = Text("Confirm path", ui.ICON_WRONG, ui.RED)
    text.normal("Path")
    text.mono(*path_lines)
    text.normal("is unknown.")
    text.normal("Are you sure?")
    return Confirm(text)


def show_qr(
    address: str,
    multisig_m: str = None,
    multisig_n: str = None,
    address_path: str = None,
) -> Confirm:
    desc = "Confirm address"
    cancel = "Address"
    if multisig_m is not None and multisig_n is not None:
        desc = "Multisig {} of {}".format(multisig_m, multisig_n)
        cancel = "XPUBs"
    elif address_path is not None:
        desc = address_path

    QR_X = const(120)
    QR_Y = const(115)
    QR_SIZE_THRESHOLD = const(63)
    QR_COEF = const(4) if len(address) < QR_SIZE_THRESHOLD else const(3)
    qr = Qr(address, QR_X, QR_Y, QR_COEF)
    text = Text(desc, ui.ICON_RECEIVE, ui.GREEN)

    return Confirm(Container(qr, text), cancel=cancel, cancel_style=ButtonDefault)


def split_address(address: str) -> Iterator[str]:
    return chunks(address, 17)  # 18 on T1


def split_op_return(data: str) -> Iterator[str]:
    if len(data) >= 18 * 5:
        data = data[: (18 * 5 - 3)] + "..."
    return chunks(data, 18)


def show_address(
    address: str,
    network: str = None,
    multisig_m: str = None,
    multisig_n: str = None,
    address_path: str = None,
) -> Confirm:
    desc = "Confirm address"
    if multisig_m is not None and multisig_n is not None:
        desc = "Multisig {} of {}".format(multisig_m, multisig_n)
    elif address_path is not None:
        desc = address_path

    text = Text(desc, ui.ICON_RECEIVE, ui.GREEN)
    if network is not None:
        text.normal("%s network" % network)
    text.mono(*split_address(address))

    return Confirm(text, cancel="QR", cancel_style=ButtonDefault)


def confirm_wipe() -> HoldToConfirm:
    text = Text("Wipe device", ui.ICON_WIPE, ui.RED)
    text.normal("Do you really want to", "wipe the device?", "")
    text.bold("All data will be lost.")
    return HoldToConfirm(text, confirm_style=ButtonCancel, loader_style=LoaderDanger)


def confirm_output(
    output_address: str = None,
    output_amount: str = None,
    output_omni_data: str = None,
    output_op_return_data: str = None,
) -> Confirm:
    if output_omni_data is not None:
        # OMNI transaction
        text = Text("OMNI transaction", ui.ICON_SEND, ui.GREEN)
        text.normal(output_omni_data)
    elif output_op_return_data is not None:
        # generic OP_RETURN
        text = Text("OP_RETURN", ui.ICON_SEND, ui.GREEN)
        text.mono(*split_op_return(output_op_return_data))
    elif output_amount is not None and output_address is not None:
        text = Text("Confirm sending", ui.ICON_SEND, ui.GREEN)
        text.normal(output_amount + " to")
        text.mono(*split_address(output_address))
    else:
        raise ValueError
    return Confirm(text)


def confirm_total(total_amount: str, fee_amount: str) -> HoldToConfirm:
    text = Text("Confirm transaction", ui.ICON_SEND, ui.GREEN)
    text.normal("Total amount:")
    text.bold(total_amount)
    text.normal("including fee:")
    text.bold(fee_amount)
    return HoldToConfirm(text)


def confirm_joint_total(spending_amount: str, total_amount: str) -> HoldToConfirm:
    text = Text("Joint transaction", ui.ICON_SEND, ui.GREEN)
    text.normal("You are contributing:")
    text.bold(spending_amount)
    text.normal("to the total amount:")
    text.bold(total_amount)
    return HoldToConfirm(text)


def confirm_feeoverthreshold(fee_amount: str) -> Confirm:
    text = Text("High fee", ui.ICON_SEND, ui.GREEN)
    text.normal("The fee of")
    text.bold(fee_amount)
    text.normal("is unexpectedly high.", "Continue?")
    return Confirm(text)


def confirm_change_count_over_threshold(change_count: str) -> Confirm:
    text = Text("Warning", ui.ICON_SEND, ui.GREEN)
    text.normal("There are {}".format(change_count))
    text.normal("change-outputs.")
    text.br_half()
    text.normal("Continue?")
    return Confirm(text)


def confirm_nondefault_locktime(
    lock_time_disabled: str = None,
    lock_time_height: str = None,
    lock_time_stamp: str = None,
) -> Confirm:
    if lock_time_disabled == "True":
        text = Text("Warning", ui.ICON_SEND, ui.GREEN)
        text.normal("Locktime is set but will", "have no effect.")
        text.br_half()
    else:
        text = Text("Confirm locktime", ui.ICON_SEND, ui.GREEN)
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
    return Confirm(text)


# debug.py
def warn_loading_seed() -> Confirm:
    text = Text("Loading seed")
    text.bold("Loading private seed", "is not recommended.")
    text.normal("Continue only if you", "know what you are doing!")
    return Confirm(text)
