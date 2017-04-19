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
from apps import fido_u2f

# Initialize all applications
if __debug__:
    debug.boot()
homescreen.boot()
management.boot()
wallet.boot()
ethereum.boot()
fido_u2f.boot()

# HACK: keep storage loaded at all times
from apps.common import storage

# Change backlight to white for better visibility
ui.display.backlight(ui.BACKLIGHT_NORMAL)

# Register USB ifaces
usb = msg.USB(
    vendor_id=0x1209,
    product_id=0x53C1,
    release_num=0x0002,
    manufacturer_str="manufacturer_str",
    product_str="product_str",
    serial_number_str="serial_number_str",
    configuration_str="configuration_str",
    interface_str="interface_str",
)
hid_wire_iface = const(0x00)
hid_wire_rdesc = bytes([
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
])
hid_wire = msg.HID(
    iface_num=hid_wire_iface,
    ep_in=0x81,
    ep_out=0x01,
    report_desc=hid_wire_rdesc,
)
msg.init_usb(usb, (hid_wire,))

# Initialize the wire codec pipeline
wire.setup(hid_wire_iface)

# Load default homescreen
from apps.homescreen.homescreen import layout_homescreen

# Run main even loop and specify which screen is default
trezor.main.run(default_workflow=layout_homescreen)
