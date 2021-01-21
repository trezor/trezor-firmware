import configparser
import sys

from device.t1 import TrezorOne
from device.tt import TrezorT


def main(model: str, file: str = None):
    config = configparser.ConfigParser()
    config.read_file(open("hardware.cfg"))
    t1 = TrezorOne(
        config["t1"]["uhub_location"],
        config["t1"]["arduino_serial"],
        config["t1"]["port"],
    )
    tt = TrezorT(config["tt"]["uhub_location"], config["tt"]["port"])

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
