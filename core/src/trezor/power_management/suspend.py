from trezor import io, log

_HANDLED_WAKEUP_FLAGS = (
    io.pm.WAKEUP_FLAG_BUTTON,
    io.pm.WAKEUP_FLAG_BLE,
    io.pm.WAKEUP_FLAG_USB,
    io.pm.WAKEUP_FLAG_POWER,
    io.pm.WAKEUP_FLAG_TOUCH,
)

if __debug__:
    _NAMED_WAKEUP_FLAGS = {
        io.pm.WAKEUP_FLAG_BUTTON: "BUTTON",
        io.pm.WAKEUP_FLAG_BLE: "BLE",
        io.pm.WAKEUP_FLAG_POWER: "POWER",
        io.pm.WAKEUP_FLAG_NFC: "NFC",
        io.pm.WAKEUP_FLAG_RTC: "RTC",
        io.pm.WAKEUP_FLAG_USB: "USB",
        io.pm.WAKEUP_FLAG_TOUCH: "TOUCH",
    }


def suspend_device() -> int:
    """Suspend the device and wait for a wakeup event. Wakeup flag is returned."""
    while True:
        if __debug__:
            log.debug(__name__, "Suspending device...")
        wakeup_flag = io.pm.suspend()
        if __debug__:
            log.debug(
                __name__, "Awoke, wakeup flag: %s", _NAMED_WAKEUP_FLAGS[wakeup_flag]
            )
        if wakeup_flag not in _HANDLED_WAKEUP_FLAGS:
            # other wakeup flags are ignored, suspend again
            continue
        return wakeup_flag
