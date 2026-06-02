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
        t1.update_firmware(file)
    else:
        model_name = {
            "T2T1": "Trezor T",
            "T2B1": "Safe 3",
            "T3B1": "Safe 3",
            "T3T1": "Safe 5",
            "T3W1": "Safe 7",
        }[model]
        tt.update_firmware(file, model_name)


if __name__ == "__main__":
    model = sys.argv[1]
    if len(sys.argv) == 3:
        main(model, file=sys.argv[2])
    else:
        main(model)
