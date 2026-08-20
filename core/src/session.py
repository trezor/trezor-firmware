# isort: skip_file
from trezor import log, loop, utils, wire, workflow

import apps.base
from apps.common import lock_manager
import usb

apps.base.boot()

if not utils.BITCOIN_ONLY and usb.ENABLE_IFACE_WEBAUTHN:
    import apps.webauthn

    apps.webauthn.boot()

if __debug__:
    import apps.debug

    apps.debug.boot()

# run main event loop and specify which screen is the default
lock_manager.boot()
workflow.start_default()

# The interfaces THP will serve. The WARD service interface joins the list when this build serves
# WARD over its own channel: it needs its own interface so the device can talk to the service while
# a wallet workflow is live on another one -- see `wire.buffers_provider_for`.
_ifaces = [usb.iface_wire]
if utils.USE_WARD_SERVICE_CHANNEL:
    _ifaces.append(usb.iface_ward)
if utils.USE_BLE:
    import trezorble as ble

    _ifaces.append(ble.interface)

wire.setup(*_ifaces)

# start the event loop
loop.run()

if __debug__:
    log.debug(__name__, "Restarting main loop")
