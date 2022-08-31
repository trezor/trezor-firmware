# isort:skip_file
# fmt: off

# We are tightly controlling the memory layout. Order of imports is important.
# Modules imported directly from here also must take care to have as few dependencies
# as possible.

# === Import always-active modules
# trezor imports only C modules
import trezor  # noqa: F401
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

# === Prepare the USB interfaces first. Do not connect to the host yet.
# usb imports trezor.utils and trezor.io which is a C module
import usb

# create an unimport manager that will be reused in the main loop
unimport_manager = utils.unimport()

# set last unlock time, unload afterwards
with unimport_manager:
    from apps.common.request_pin import set_last_unlock_time
    set_last_unlock_time()
    del set_last_unlock_time

# start the USB
import storage.device

usb.bus.open(storage.device.get_device_id())

# run the endless loop
while True:
    with unimport_manager:
        import session  # noqa: F401
        del session
