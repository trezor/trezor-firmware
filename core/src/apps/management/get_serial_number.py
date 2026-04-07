from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import GetSerialNumber, SerialNumber


async def get_serial_number(msg: GetSerialNumber) -> SerialNumber:
    from trezor import TR
    from trezor.messages import SerialNumber
    from trezor.ui.layouts import confirm_action
    from trezor.utils import serial_number

    serial_number = serial_number()
    await confirm_action(
        br_name="get_serial_number",
        title=TR.sn__title,
        action=TR.sn__action,
        description=f"\n{serial_number}",
        verb=TR.buttons__allow,
    )
    return SerialNumber(serial_number=serial_number)
