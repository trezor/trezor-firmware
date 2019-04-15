import trezorio as io

iface_wire = io.WebUSB(
    iface_num=0,
    ep_in=0x81,
    ep_out=0x01,
)

iface_vcp = io.VCP(
    iface_num=2,
    data_iface_num=3,
    ep_in=0x83,
    ep_out=0x03,
    ep_cmd=0x84,
)

bus = io.USB(
    vendor_id=0x1209,
    product_id=0x53C1,
    release_num=0x0100,
    manufacturer="SatoshiLabs",
    product="TREZOR",
    interface="TREZOR Interface",
    serial_number="1234",
    usb21_landing=False,
)

bus.add(iface_wire)
bus.add(iface_vcp)
