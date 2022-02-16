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
utils.presize_module("trezor", 30)

# storage imports storage.common, storage.cache and storage.device.
# These import trezor, trezor.config (which is a C module), trezor.utils, and each other.
import storage
# we will need space for 12 items in the storage module
utils.presize_module("storage", 12)

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

# usb imports trezor.utils and trezor.io which is a C module
import usb
# opening empty usb
usb.bus.open("355C817510C0EABF2F147145")  # random 12byte hex

# create an unimport manager that will be reused in the main loop
unimport_manager = utils.unimport()

# unlock the device, unload the boot module afterwards
with unimport_manager:
    import boot
    del boot

# closing the empty USB, adding the interfaces and starting it again
usb.bus.close()
usb.add_interfaces()

import storage.device

usb.bus.open(storage.device.get_device_id())

# run the endless loop
while True:
    with unimport_manager:
        import session  # noqa: F401
        del session
