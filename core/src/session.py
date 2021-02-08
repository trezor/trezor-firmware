
def _boot_apps() -> None:
    import usb
    from trezor import workflow, utils

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


def handle(state):
    import usb
    from trezor import loop, wire
    from storage import cache
    cache.set_state(state)
    _boot_apps()
    wire.setup(usb.iface_wire)
    if __debug__:
        wire.setup(usb.iface_debug, use_workflow=False)
    loop.run()
