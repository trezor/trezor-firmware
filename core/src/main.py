# isort:skip_file
# fmt: off

# Import always-active modules
import storage
import storage.device
if __debug__:
    import storage.debug

import trezor
import trezor.pin  # noqa: F401
from trezor import utils

utils.presize_module("trezor", 30)
utils.presize_module("storage", 12)

if not utils.BITCOIN_ONLY:
    import storage.fido2  # noqa: F401

# Prepare the USB interfaces first. Do not connect to the host yet.
import usb

unimport_manager = utils.unimport()

# unlock the device, unload the boot module afterwards
with unimport_manager:
    import boot
    del boot

# start the USB
usb.bus.open(storage.device.get_device_id())

while True:
    with unimport_manager:
        import session  # noqa: F401
        del session
