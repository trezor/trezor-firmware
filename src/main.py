import trezor.main
from trezor import msg
from trezor import ui
from trezor import wire

# Load all applications
from apps import homescreen
from apps import management
from apps import wallet

# Initialize all applications
homescreen.boot()
management.boot()
wallet.boot()

# Change backlight to white for better visibility
ui.display.backlight(ui.BACKLIGHT_NORMAL)

# Just a demo to show how to register USB ifaces
msg.setup([(1, 0xF53C), (2, 0xF1D0)])

# Initialize the wire codec pipeline
wire.setup()

# Load default homescreen
from apps.homescreen.layout_homescreen import layout_homescreen

# Run main even loop and specify, which screen is default
trezor.main.run(default_workflow=layout_homescreen)
