import trezor.main
from trezor import msg

# Load all applications
from apps import playground
from apps import homescreen
from apps import management
from apps import wallet

# Initialize all applications
playground.boot()
homescreen.boot()
management.boot()
wallet.boot()

# just a demo to show how to register USB ifaces
msg.setup([(1, 0xF53C), (2, 0xF1D0)])

# Load default homescreen
from apps.homescreen.layout_homescreen import layout_homescreen

# Run main even loop and specify, which screen is default
trezor.main.run(main_layout=layout_homescreen)
