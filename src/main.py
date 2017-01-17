import trezor.main
from trezor import msg
from trezor import ui
from trezor import wire

# Load all applications
if __debug__:
    from apps import debug
from apps import homescreen
from apps import management
from apps import wallet
from apps import ethereum

# Initialize all applications
if __debug__:
    debug.boot()
homescreen.boot()
management.boot()
wallet.boot()
ethereum.boot()

# HACK: keep storage loaded at all times
from apps.common import storage

# Change backlight to white for better visibility
ui.display.backlight(ui.BACKLIGHT_NORMAL)

# Just a demo to show how to register USB ifaces
msg.set_interfaces([0xFF00, 0xFF01, 0xF1D0])
# and list them
for i, up in enumerate(msg.get_interfaces()):
    print("iface %d: usage_page 0x%04x" % (i + 1, up))

# Initialize the wire codec pipeline
wire.setup(0xFF00)

# Load default homescreen
from apps.homescreen.homescreen import layout_homescreen

# Run main even loop and specify which screen is default
trezor.main.run(default_workflow=layout_homescreen)
