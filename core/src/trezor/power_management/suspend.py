from trezor import io

_HANDLED_WAKEUP_FLAGS = (
    io.pm.WAKEUP_FLAG_BUTTON,
    io.pm.WAKEUP_FLAG_BLE,
    io.pm.WAKEUP_FLAG_POWER,
)


def suspend_device() -> int:
    """Suspend the device and wait for a wakeup event. Wakeup flag is returned."""
    while True:
        wakeup_flag = io.pm.suspend()
        if wakeup_flag not in _HANDLED_WAKEUP_FLAGS:
            # other wakeup flags are ignored, suspend again
            continue
        return wakeup_flag
