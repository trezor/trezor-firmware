# isort:skip_file

# unlock the device
import boot  # noqa: F401

# prepare the USB interfaces, but do not connect to the host yet
import usb

from trezor import loop, wire, workflow, utils

# load applications
import apps.homescreen
import apps.management
import apps.wallet
import apps.ethereum
import apps.lisk
import apps.nem

if __debug__:
    import apps.debug
else:
    import apps.fido_u2f

# boot applications
apps.homescreen.boot()
apps.management.boot()
apps.wallet.boot()
apps.ethereum.boot()
apps.lisk.boot()
apps.nem.boot()
if __debug__:
    apps.debug.boot()
else:
    apps.fido_u2f.boot(usb.iface_u2f)

# initialize the wire codec and start the USB
wire.setup(usb.iface_wire)
if __debug__:
    wire.setup(usb.iface_debug)
usb.bus.open()

# switch into unprivileged mode, as we don't need the extra permissions anymore
utils.set_mode_unprivileged()

# run main event loop and specify which screen is the default
from apps.homescreen.homescreen import homescreen

workflow.startdefault(homescreen)
loop.run()
