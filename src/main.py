from micropython import const

import trezor.main
from trezor import msg
from trezor import ui
from trezor import wire

# Load all applications
if __debug__:
    from apps import debug
from apps import homescreen
from apps import management
from apps import wallet
from apps import ethereum
# from apps import fido_u2f

# Initialize all applications
if __debug__:
    debug.boot()
homescreen.boot()
management.boot()
wallet.boot()
ethereum.boot()
# fido_u2f.boot()

# HACK: keep storage loaded at all times
from apps.common import storage

# Change backlight to white for better visibility
ui.display.backlight(ui.BACKLIGHT_NORMAL)

# Register USB ifaces

_IFACE_WIRE = const(0x00)
_IFACE_U2F = const(0x00)
_IFACE_VCP = const(0x01)
_IFACE_VCP_DATA = const(0x02)

hid_wire = msg.HID(
    iface_num=_IFACE_WIRE,
    ep_in=0x81,
    ep_out=0x01,
    report_desc=bytes([
        0x06, 0x00, 0xff,  # USAGE_PAGE (Vendor Defined)
        0x09, 0x01,        # USAGE (1)
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

hid_u2f = msg.HID(
    iface_num=_IFACE_U2F,
    ep_in=0x81,
    ep_out=0x01,
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

vcp = msg.VCP(
    iface_num=_IFACE_VCP,
    data_iface_num=_IFACE_VCP_DATA,
    ep_in=0x82,
    ep_out=0x02,
    ep_cmd=0x83,
)

msg.init_usb(msg.USB(
    vendor_id=0x1209,
    product_id=0x53C1,
    release_num=0x0002,
    manufacturer_str="SatoshiLabs",
    product_str="TREZOR",
    serial_number_str="000000000000000000000000"
), (hid_wire, vcp))

# Initialize the wire codec pipeline
wire.setup(_IFACE_WIRE)

# Load default homescreen
from apps.homescreen.homescreen import layout_homescreen

# Run main even loop and specify which screen is default
trezor.main.run(default_workflow=layout_homescreen)
