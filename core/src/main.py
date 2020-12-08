# isort:skip_file

import utime

_start_ticks = utime.ticks_ms()

# unlock the device
import boot  # noqa: F401

_boot_ticks = utime.ticks_ms()

# prepare the USB interfaces, but do not connect to the host yet
import usb

from trezor import loop, utils, wire, workflow

# start the USB
usb.bus.open()

_usb_ticks = utime.ticks_ms()


def _boot_apps() -> None:
    # load applications
    import apps.base
    import apps.management
    import apps.bitcoin
    import apps.misc

    if not utils.BITCOIN_ONLY:
        import apps.ethereum
        import apps.lisk
        import apps.monero
        import apps.nem
        import apps.stellar
        import apps.ripple
        import apps.cardano
        import apps.tezos
        import apps.eos
        import apps.binance
        import apps.webauthn

    if __debug__:
        import apps.debug

    # boot applications
    apps.base.boot()
    apps.management.boot()
    apps.bitcoin.boot()
    apps.misc.boot()
    if not utils.BITCOIN_ONLY:
        apps.ethereum.boot()
        apps.lisk.boot()
        apps.monero.boot()
        apps.nem.boot()
        apps.stellar.boot()
        apps.ripple.boot()
        apps.cardano.boot()
        apps.tezos.boot()
        apps.eos.boot()
        apps.binance.boot()
        apps.webauthn.boot()
    if __debug__:
        apps.debug.boot()

    # run main event loop and specify which screen is the default
    apps.base.set_homescreen()
    workflow.start_default()


_boot_apps()

# initialize the wire codec
wire.setup(usb.iface_wire)
if __debug__:
    wire.setup(usb.iface_debug, use_workflow=False)

_wire_ticks = utime.ticks_ms()

import apps.base
apps.base.timings = "boot:%d, usb:%d, wire:%d (total %d)" % (
    utime.ticks_diff(_boot_ticks, _start_ticks),
    utime.ticks_diff(_usb_ticks, _boot_ticks),
    utime.ticks_diff(_wire_ticks, _usb_ticks),
    utime.ticks_diff(_wire_ticks, _start_ticks))

loop.run()

# loop is empty. That should not happen
utils.halt("All tasks have died.")
