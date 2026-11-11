from trezor import io, utils

bus = io.USB()

ENABLE_IFACE_WEBAUTHN = not utils.BITCOIN_ONLY

if utils.USE_WARD_SERVICE_CHANNEL:
    iface_ward = io.USBIF(handle=io.USBIF_WARD)

iface_wire = io.USBIF(handle=io.USBIF_WIRE)
iface_debug = io.USBIF(handle=io.USBIF_DEBUG)
iface_webauthn = io.USBIF(handle=io.USBIF_WEBAUTHN)
