import trezor.main
from trezor import msg

# Load all applications
from apps import playground
from apps import homescreen
from apps import management
from apps import wallet
from apps import seed

# Initialize all applications
playground.boot()
homescreen.boot()
management.boot()
wallet.boot()
seed.boot()

#change backlight to white for better visibility
trezor.ui.display.backlight(255)

# just a demo to show how to register USB ifaces
msg.setup([(1, 0xF53C), (2, 0xF1D0)])

# Load default homescreen
from apps.seed.layout_seed import layout_seed

# Run main even loop and specify, which screen is default
trezor.main.run(main_layout=layout_seed)
