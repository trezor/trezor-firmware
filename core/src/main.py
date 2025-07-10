# isort:skip_file
# fmt: off

# We are tightly controlling the memory layout. Order of imports is important.
# Modules imported directly from here also must take care to have as few dependencies
# as possible.

# === Import always-active modules
# trezor imports only C modules
import trezor
# trezor.utils import only C modules
from trezor import utils
# we need space for 30 items in the trezor module
utils.presize_module(trezor, 30)

# storage imports storage.common, storage.cache and storage.device.
# These import trezor, trezor.config (which is a C module), trezor.utils, and each other.
import storage
# we will need space for XX items in the storage module
utils.presize_module(storage, 20)

if not utils.BITCOIN_ONLY:
    # storage.fido2 only imports C modules
    import storage.fido2  # noqa: F401

if __debug__:
    # storage.debug only imports C modules
    import storage.debug

# trezor.pin imports trezor.utils
# We need it as an always-active module because trezor.pin.show_pin_timeout is used
# as a UI callback for storage, which can be invoked at any time
import trezor.pin  # noqa: F401

# === Prepare the USB interfaces first. Do not connect to the host yet.
# usb imports trezor.utils and trezor.io which is a C module
import usb

# unlock the device, unload the boot module afterwards
with utils.unimport():
    import boot
    del boot

# start the USB
import storage.device

usb.bus.open(storage.device.get_device_id())


# enable BLE, allow connections
if utils.USE_BLE:
    with utils.unimport():
        import ble  # noqa: F401
        del ble


# run the endless loop
unimport_manager = utils.unimport()
while True:
    with unimport_manager:
        import session  # noqa: F401
        del session
