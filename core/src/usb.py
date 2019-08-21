from trezor import io

from apps.common.storage.device import get_device_id

# fmt: off

# interface used for trezor wire protocol
iface_wire = io.WebUSB(
    iface_num=0,
    ep_in=0x81,
    ep_out=0x01,
)

# as the iface_vcp interface can have at most 3 endpoints, we cannot use it simultaneously
# with the iface_webauthn interface.
if __debug__:
    # interface used for debug messages with trezor wire protocol
    iface_debug = io.WebUSB(
        iface_num=1,
        ep_in=0x82,
        ep_out=0x02,
    )
    # interface used for cdc/vcp console emulation (debug messages)
    iface_vcp = io.VCP(
        iface_num=2,
        data_iface_num=3,
        ep_in=0x83,
        ep_out=0x03,
        ep_cmd=0x84,
    )
else:
    # interface used for FIDO/U2F and FIDO2/WebAuthn HID transport
    iface_webauthn = io.HID(
        iface_num=1,
        ep_in=0x82,
        ep_out=0x02,
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
    )

bus = io.USB(
    vendor_id=0x1209,
    product_id=0x53C1,
    release_num=0x0200,
    manufacturer="SatoshiLabs",
    product="TREZOR",
    interface="TREZOR Interface",
    serial_number=get_device_id(),
)
bus.add(iface_wire)
if __debug__:
    bus.add(iface_debug)
    bus.add(iface_vcp)
else:
    bus.add(iface_webauthn)
