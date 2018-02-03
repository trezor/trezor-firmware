import boot

from trezor import io
from trezor import log
from trezor import loop
from trezor import wire
from trezor import workflow

log.level = log.DEBUG

# initialize the USB stack

usb_wire = io.WebUSB(
    iface_num=0,
    ep_in=0x81,
    ep_out=0x01,
)

usb_u2f = io.HID(
    iface_num=3,
    ep_in=0x84,
    ep_out=0x03,
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

if __debug__:
    usb_debug = io.WebUSB(
        iface_num=4,
        ep_in=0x85,
        ep_out=0x04,
    )
    usb_vcp = io.VCP(
        iface_num=1,
        data_iface_num=2,
        ep_in=0x82,
        ep_out=0x02,
        ep_cmd=0x83,
    )

usb = io.USB(
    vendor_id=0x1209,
    product_id=0x53C1,
    release_num=0x0200,
    manufacturer="SatoshiLabs",
    product="TREZOR",
    serial_number="44DD6B2C788D760538A78ECA",
    interface="TREZOR Interface",
)

usb.add(usb_wire)
usb.add(usb_u2f)
if __debug__:
    usb.add(usb_debug)
    usb.add(usb_vcp)

# load applications
if __debug__:
    from apps import debug
from apps import homescreen
from apps import management
from apps import wallet
from apps import ethereum
from apps import fido_u2f

# boot applications
if __debug__:
    debug.boot()
homescreen.boot()
management.boot()
wallet.boot()
ethereum.boot()
fido_u2f.boot(usb_u2f)

# initialize the wire codec and start the USB
wire.setup(usb_wire)
if __debug__:
    wire.setup(usb_debug)
usb.open()

# load default homescreen
from apps.homescreen.homescreen import layout_homescreen

# run main even loop and specify which screen is default
workflow.startdefault(layout_homescreen)
loop.run()
