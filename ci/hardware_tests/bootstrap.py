import os
import sys

from device.core import TrezorCore
from device.legacy import TrezorOne

# https://www.uugear.com/product/mega4-4-port-usb-3-ppps-hub-for-raspberry-pi-4b/
# as long as every runner has this hub we don't have to configure a per-runner hub location
HUB_VENDOR = "2109:2817"


def main(model: str, file: str = None):
    t1 = TrezorOne(
        os.getenv("T1_UHUB_LOCATION"),
        os.getenv("T1_ARDUINO_SERIAL"),
        os.getenv("T1_UHUB_PORT"),
    )
    tt = TrezorCore(hub_vendor=HUB_VENDOR, device_port=os.getenv("TT_UHUB_PORT"))

    if model == "T1B1":
        # tt.power_off()
        path = t1.update_firmware(file)
    elif model == "T2T1":
        # t1.power_off()
        path = tt.update_firmware(file, "Trezor T")
    elif model == "T2B1":
        path = tt.update_firmware(file, "Safe 3")
    else:
        raise ValueError("Unknown Trezor model.")

    print(path)


if __name__ == "__main__":
    model = sys.argv[1]
    if len(sys.argv) == 3:
        main(model, file=sys.argv[2])
    else:
        main(model)
