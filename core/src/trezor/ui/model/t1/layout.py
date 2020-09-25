from micropython import const

from trezor.messages import BackupType
from trezor.ui.qr import Qr
from trezor.utils import chunks

from .confirm import Confirm
from .text import Text

if False:
    from typing import Iterator
    from ..common import ListsArg


def confirm_ping() -> Confirm:
    text = Text("PING")
    text.normal("Ping.")
    return Confirm(text)


def confirm_reset_device(backup_type: str) -> Confirm:
    text = Text(new_lines=False)  # FIXME new_lines?
    if backup_type == str(BackupType.Slip39_Basic):
        text.bold("Create a new wallet")
        text.br()
        text.bold("with Shamir Backup?")
    elif backup_type == str(BackupType.Slip39_Advanced):
        text.bold("Create a new wallet")
        text.br()
        text.bold("with Super Shamir?")
    else:
        text.bold("Do you want to")
        text.br()
        text.bold("create a new wallet?")

    text.br()
    text.br_half()
    text.normal("By continuing you agree")
    text.br()
    text.normal("to")
    text.bold("trezor.io/tos")
    return Confirm(text, confirm="CREATE", cancel="CANCEL")


# no mockup
# First prompt
def confirm_backup1() -> Confirm:
    text = Text(new_lines=False)
    text.bold("New wallet created")
    text.br()
    text.bold("successfully!")
    text.br()
    text.br_half()
    text.normal("You should back up your")
    text.br()
    text.normal("new wallet right now.")
    return Confirm(text, confirm="BACKUP", cancel="NO")


# no mockup
# If the user selects Skip, ask again
def confirm_backup2() -> Confirm:
    text = Text("Skip the backup?", new_lines=False)
    text.normal("You can back up ", "your Trezor once, ", "at any time.")
    return Confirm(text, confirm="BACKUP", cancel="NO")


def confirm_path_warning(_lists: ListsArg) -> Confirm:
    path_lines = _lists["path_lines"]
    assert isinstance(path_lines, list)
    text = Text("WRONG ADDRESS PATH")
    text.br_half()
    text.mono(*path_lines)
    text.br_half()
    text.normal("Are you sure?")
    return Confirm(text)


def show_qr(
    address: str,
    multisig_m: str = None,
    multisig_n: str = None,
    address_path: str = None,
) -> Confirm:

    QR_X = const(32)
    QR_Y = const(32)
    QR_SIZE_THRESHOLD = const(43)
    QR_COEF = const(2) if len(address) < QR_SIZE_THRESHOLD else const(1)
    qr = Qr(address, QR_X, QR_Y, QR_COEF)

    return Confirm(qr, confirm="CONTINUE", cancel="")


def split_address(address: str) -> Iterator[str]:
    return chunks(address, 17)


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
    desc = "CONFIRM ADDRESS"
    cancel = "QR CODE"
    if multisig_m is not None and multisig_n is not None:
        desc = "MULTISIG {} OF {}".format(multisig_m, multisig_n)
    elif address_path is not None:
        desc = address_path

    text = Text(desc)
    if network is not None:
        text.normal("%s network" % network)
    text.bold("Address:")
    text.mono(*split_address(address))
    return Confirm(text, confirm="CONTINUE", cancel=cancel)


def confirm_wipe() -> Confirm:
    text = Text(new_lines=False)
    text.bold("Do you want to wipe")
    text.br()
    text.bold("the device?")
    text.br()
    text.br_half()
    text.normal("All data will be lost.")
    return Confirm(text, confirm="WIPE DEVICE", cancel="CANCEL")


# FIXME: needs to be one pageable layout containing all layouts
def confirm_output(
    output_address: str = None,
    output_amount: str = None,
    output_omni_data: str = None,
    output_op_return_data: str = None,
) -> Confirm:
    if output_omni_data is not None:
        # OMNI transaction
        text = Text("OMNI TRANSACTION")
        text.normal(output_omni_data)
    elif output_op_return_data is not None:
        # generic OP_RETURN
        text = Text("OP_RETURN")
        text.mono(*split_op_return(output_op_return_data))
    elif output_amount is not None and output_address is not None:
        text = Text("TRANSACTION")
        text.normal("Send " + output_amount + " to")
        text.mono(*split_address(output_address))
    else:
        raise ValueError
    return Confirm(text, confirm="NEXT", cancel="CANCEL")


def confirm_total(total_amount: str, fee_amount: str) -> Confirm:
    text = Text("TRANSACTION")
    text.bold("Total amount:")
    text.mono(total_amount)
    text.bold("Fee included:")
    text.mono(fee_amount)
    return Confirm(text, confirm="HOLD TO CONFIRM", cancel="X")


def confirm_joint_total(spending_amount: str, total_amount: str) -> Confirm:
    text = Text("JOINT TRANSACTION")
    text.bold("You are contributing:")
    text.mono(spending_amount)
    text.bold("to the total amount:")
    text.mono(total_amount)
    return Confirm(text, confirm="HOLD TO CONFIRM", cancel="X")


def confirm_feeoverthreshold(fee_amount: str) -> Confirm:
    text = Text("HIGH FEE")
    text.normal("The fee of")
    text.bold(fee_amount)
    text.normal("is unexpectedly high.", "Continue?")
    return Confirm(text)


def confirm_change_count_over_threshold(change_count: str) -> Confirm:
    text = Text("WARNING!")
    text.normal("There are {}".format(change_count))
    text.normal("change-outputs.")
    text.br_half()
    text.normal("Continue?")
    return Confirm(text)


_LOCKTIME_TIMESTAMP_MIN_VALUE = const(500000000)


def confirm_nondefault_locktime(
    lock_time: str, lock_time_disabled: str = None
) -> Confirm:
    if lock_time_disabled == "True":
        text = Text("WARNING!")
        text.normal("Locktime is set but will", "have no effect.")
        text.br_half()
    else:
        text = Text("CONFIRM LOCKTIME")
        text.normal("Locktime for this", "transaction is set to")
        if int(lock_time) < _LOCKTIME_TIMESTAMP_MIN_VALUE:
            text.normal("blockheight:")
        else:
            text.normal("timestamp:")
        text.bold(lock_time)

    text.normal("Continue?")
    return Confirm(text)


# debug.py
def warn_loading_seed() -> Confirm:
    text = Text()
    text.normal("Loading private seed", "is not recommended.")
    text.br_half()
    text.bold("Continue only ", "if you know", "what you are doing!")
    return Confirm(text)
