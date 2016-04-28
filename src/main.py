import trezor.main

# Load all applications
from apps import homescreen
from apps import playground
# from apps import wallet

# Initialize all applications
homescreen.boot()
playground.boot()
# wallet.boot()

# Load default homescreen
from apps.homescreen.layout_homescreen import layout_homescreen

# Run main even loop and specify, which screen is default
trezor.main.run(main_layout=layout_homescreen)
