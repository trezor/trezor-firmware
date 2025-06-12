from trezor import io, workflow

from apps.base import set_homescreen
from apps.homescreen import chargingscreen


def suspend_device(close_others: bool = True) -> None:
    if io.pm.is_usb_connected():
        return
    if close_others:
        workflow.close_others()
    while True:
        wakeup_flag = io.pm.suspend()
        if wakeup_flag in (io.pm.WAKEUP_FLAG_BUTTON, io.pm.WAKEUP_FLAG_BLE):
            # regular waking up by button or BLE
            set_homescreen()
            break
        elif wakeup_flag == io.pm.WAKEUP_FLAG_POWER:
            # charging started
            if io.pm.is_usb_connected():
                set_homescreen()
            else:
                set_chargingscreen()
            break
        else:
            # other wakup flags are ignored, suspend again
            continue


def set_chargingscreen() -> None:
    """Set the charging screen when the device is woken up by power button."""
    workflow.set_default(chargingscreen, restart=True)
