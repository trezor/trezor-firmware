import os
import sys

from device.t1 import TrezorOne
from device.tt import TrezorT


def main(model: str, file: str = None):
    t1 = TrezorOne(
        os.environ["T1_UHUB_LOCATION"],
        os.environ["T1_ARDUINO_SERIAL"],
        os.environ["T1_UHUB_PORT"],
    )
    tt = TrezorT(os.environ["TT_UHUB_LOCATION"], os.environ["TT_UHUB_PORT"])

    if model == "t1":
        tt.power_off()
        path = t1.update_firmware(file)
    elif model == "tt":
        t1.power_off()
        path = tt.update_firmware(file)
    else:
        raise ValueError("Unknown Trezor model.")

    print(path)


if __name__ == "__main__":
    model = sys.argv[1]
    if len(sys.argv) == 3:
        main(model, file=sys.argv[2])
    else:
        main(model)
