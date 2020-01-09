# isort:skip_file

# unlock the device
import boot  # noqa: F401

# prepare the USB interfaces, but do not connect to the host yet
import usb

import storage.recovery
from trezor import loop, utils, wire, workflow

# start the USB
usb.bus.open()


def _boot_apps() -> None:
    # load applications
    import apps.homescreen
    import apps.management
    import apps.wallet

    if not utils.BITCOIN_ONLY:
        import apps.ethereum
        import apps.lisk
        import apps.monero
        import apps.nem
        import apps.nem2
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
    apps.homescreen.boot()
    apps.management.boot()
    apps.wallet.boot()
    if not utils.BITCOIN_ONLY:
        apps.ethereum.boot()
        apps.lisk.boot()
        apps.monero.boot()
        apps.nem.boot()
        apps.nem2.boot()
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
    if storage.recovery.is_in_progress():
        from apps.management.recovery_device.homescreen import recovery_homescreen

        workflow.start_default(recovery_homescreen)
    else:
        from apps.homescreen.homescreen import homescreen

        workflow.start_default(homescreen)


# initialize the wire codec
wire.setup(usb.iface_wire)
if __debug__:
    wire.setup(usb.iface_debug)

_boot_apps()
loop.run()

# loop is empty. That should not happen
utils.halt("All tasks have died.")
