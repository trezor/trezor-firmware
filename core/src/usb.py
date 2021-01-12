from storage.device import get_device_id
from trezor import io, utils

_iface_iter = iter(range(5))

ENABLE_IFACE_DEBUG = __debug__
# change to False to enable VCP, see below
ENABLE_IFACE_WEBAUTHN = not utils.BITCOIN_ONLY

# We only have 10 available USB endpoints on real HW, of which 2 are taken up by the USB descriptor.
# iface_wire, iface_debug and iface_webauthn also consume 2 each, iface_vcp uses 3.
# That is a grand total of 11. That means that we can't enable everything at the same time.
# By default, iface_vcp is only enabled on bitcoin_only firmware, where iface_webauthn
# is disabled. Implementation-wise, we check if any of the previous ifaces is disabled
# in order to enable VCP.
ENABLE_IFACE_VCP = __debug__ and (
    utils.EMULATOR or not ENABLE_IFACE_DEBUG or not ENABLE_IFACE_WEBAUTHN
)

# interface used for trezor wire protocol
id_wire = next(_iface_iter)
iface_wire = io.WebUSB(
    iface_num=id_wire,
    ep_in=0x81 + id_wire,
    ep_out=0x01 + id_wire,
)

# XXXXXXXXXXXXXXXXXXX
#
# We want the following branches present only in their respective firmwares. To achieve
# that, we are taking advantage of the upy compiler static optimization: when an
# if-expression statically evaluates to False, the branch is excluded from the bytecode.
# This works magically for the __debug__ builtin, and `utils.BITCOIN_ONLY` is replaced
# by a literal True/False by us in the build step.
#
# Therefore, each of the following needs to include the respective static expression
# so that it can be correctly excluded from the resulting build.

if __debug__ and ENABLE_IFACE_DEBUG:
    # interface used for debug messages with trezor wire protocol
    id_debug = next(_iface_iter)
    iface_debug = io.WebUSB(
        iface_num=id_debug,
        ep_in=0x81 + id_debug,
        ep_out=0x01 + id_debug,
    )

if not utils.BITCOIN_ONLY and ENABLE_IFACE_WEBAUTHN:
    # interface used for FIDO/U2F and FIDO2/WebAuthn HID transport
    id_webauthn = next(_iface_iter)
    iface_webauthn = io.HID(
        iface_num=id_webauthn,
        ep_in=0x81 + id_webauthn,
        ep_out=0x01 + id_webauthn,
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

if __debug__ and ENABLE_IFACE_VCP:
    # interface used for cdc/vcp console emulation (debug messages)
    id_vcp = next(_iface_iter)
    id_vcp_data = next(_iface_iter)
    iface_vcp = io.VCP(
        iface_num=id_vcp,
        data_iface_num=id_vcp_data,
        ep_in=0x81 + id_vcp,
        ep_out=0x01 + id_vcp,
        ep_cmd=0x81 + id_vcp_data,
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
if __debug__ and ENABLE_IFACE_DEBUG:
    bus.add(iface_debug)
if not utils.BITCOIN_ONLY and ENABLE_IFACE_WEBAUTHN:
    bus.add(iface_webauthn)
if __debug__ and ENABLE_IFACE_VCP:
    bus.add(iface_vcp)
