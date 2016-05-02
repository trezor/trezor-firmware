import trezor.main

from apps import playground_stick
playground_stick.boot()

from apps.playground_stick import layout_homescreen
# Run main even loop and specify, which screen is default
trezor.main.run(main_layout=layout_homescreen.layout_homescreen)
