from trezor import io, utils

bus = io.USB()

ENABLE_IFACE_WEBAUTHN = not utils.BITCOIN_ONLY

iface_wire = io.USBIF(handle=io.USBIF_WIRE)
iface_debug = io.USBIF(handle=io.USBIF_DEBUG)
iface_webauthn = io.USBIF(handle=io.USBIF_WEBAUTHN)

# The WARD service interface, when this build serves WARD over its own channel rather than over the
# ordinary connection. Gated on the WARD transport itself, NOT on `ENABLE_IFACE_WEBAUTHN`: that is
# the coin-support axis and has nothing to say about which transport WARD uses.
if utils.USE_WARD_SERVICE_CHANNEL:
    iface_ward = io.USBIF(handle=io.USBIF_WARD)
