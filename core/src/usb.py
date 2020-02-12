from storage.device import get_device_id
from trezor import io, utils

# interface used for trezor wire protocol
iface_wire = io.WebUSB(iface_num=0, ep_in=0x81, ep_out=0x01)

if __debug__:
    # interface used for debug messages with trezor wire protocol
    iface_debug = io.WebUSB(iface_num=1, ep_in=0x82, ep_out=0x02)

if not utils.BITCOIN_ONLY:
    # interface used for FIDO/U2F and FIDO2/WebAuthn HID transport
    iface_webauthn = io.HID(
        iface_num=2 if __debug__ else 1,
        ep_in=0x83 if __debug__ else 0x82,
        ep_out=0x03 if __debug__ else 0x02,
        # fmt: off
        report_desc=bytes([
            0x06, 0xd0, 0xf1,  # USAGE_PAGE (FIDO Alliance)
            0x09, 0x01,        # USAGE (U2F HID Authenticator Device)
            0xa1, 0x01,        # COLLECTION (Application)
            0x09, 0x20,        # USAGE (Input Report Data)
            0x15, 0x00,        # LOGICAL_MINIMUM (0)
            0x26, 0xff, 0x00,  # LOGICAL_MAXIMUM (255)
            0x75, 0x08,        # REPORT_SIZE (8)
            0x95, 0x40,        # REPORT_COUNT (64)
            0x81, 0x02,        # INPUT (Data,Var,Abs)
            0x09, 0x21,        # USAGE (Output Report Data)
            0x15, 0x00,        # LOGICAL_MINIMUM (0)
            0x26, 0xff, 0x00,  # LOGICAL_MAXIMUM (255)
            0x75, 0x08,        # REPORT_SIZE (8)
            0x95, 0x40,        # REPORT_COUNT (64)
            0x91, 0x02,        # OUTPUT (Data,Var,Abs)
            0xc0,              # END_COLLECTION
        ]),
        # fmt: on
    )

if __debug__:
    # We cannot use this on real device simultaneously with the iface_webauthn
    # interface, because we have only limited number of endpoints (10).
    # We start this only for bitcoin-only firmware or for emulator.
    ENABLE_VCP_IFACE = utils.EMULATOR or utils.BITCOIN_ONLY
    if ENABLE_VCP_IFACE:
        # interface used for cdc/vcp console emulation (debug messages)
        iface_vcp = io.VCP(
            iface_num=2 if utils.BITCOIN_ONLY else 3,
            data_iface_num=3 if utils.BITCOIN_ONLY else 4,
            ep_in=0x83 if utils.BITCOIN_ONLY else 0x84,
            ep_out=0x03 if utils.BITCOIN_ONLY else 0x04,
            ep_cmd=0x84 if utils.BITCOIN_ONLY else 0x85,
        )

bus = io.USB(
    vendor_id=0x1209,
    product_id=0x53C1,
    release_num=0x0200,
    manufacturer="SatoshiLabs",
    product="TREZOR",
    interface="TREZOR Interface",
    serial_number=get_device_id(),
    usb21_landing=False,
)
bus.add(iface_wire)
if __debug__:
    bus.add(iface_debug)
if not utils.BITCOIN_ONLY:
    bus.add(iface_webauthn)
if __debug__:
    if ENABLE_VCP_IFACE:
        bus.add(iface_vcp)
