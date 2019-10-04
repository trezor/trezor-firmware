import configparser
import sys

from device.t1 import TrezorOne


def main(file: str = None):
    config = configparser.ConfigParser()
    config.read_file(open("hardware.cfg"))
    t1 = TrezorOne(
        config["t1"]["location"], config["t1"]["port"], config["t1"]["arduino_serial"],
    )
    t1.update_firmware(file)


if __name__ == "__main__":
    file = None
    if len(sys.argv) == 2:
        file = sys.argv[1]
    main(file)
