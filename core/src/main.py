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

# Initializing config so that we can get device ID
import storage.device
from trezor import config
from trezor.pin import show_pin_timeout
config.init(show_pin_timeout)

# usb imports trezor.utils and trezor.io which is a C module
import usb
# opening empty usb
# There is one special case when the device ID is not there
# and cannot be set up, because the storage is not unlocked
# It happens for example after wiping the bootloader
# We are catching this error and assigning default device ID
# TODO: this logic could be moved into get_device_id(),
# and could require some kwarg, like `ignore_locked_storage=True`
try:
    device_id = storage.device.get_device_id()
except RuntimeError as err:
    if "Could not save value" not in str(err):
        raise
    device_id = "000000000000000000000000"
usb.bus.open(device_id)

# create an unimport manager that will be reused in the main loop
unimport_manager = utils.unimport()

# unlock the device, unload the boot module afterwards
with unimport_manager:
    import boot
    del boot

# closing the empty USB, adding the interfaces and starting it again
usb.bus.close()
usb.add_interfaces()

usb.bus.open(storage.device.get_device_id())

# run the endless loop
while True:
    with unimport_manager:
        import session  # noqa: F401
        del session
