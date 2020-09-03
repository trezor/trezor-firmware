import datetime
import os
import time


class Device:
    def __init__(self, uhub_location, device_port):
        self.uhub_location = uhub_location
        self.device_port = device_port

    def run_trezorctl(self, cmd: str):
        full_cmd = "trezorctl "
        full_cmd += cmd
        print("[software/trezorctl] Running '{}'".format(full_cmd))
        os.system(full_cmd)

    def check_version(self):
        self.run_trezorctl("get-features | grep version")

    def reboot(self):
        self.power_off()
        self.power_on()

    def power_on(self):
        self.now()
        print("[hardware/usb] Turning power on...")
        os.system(
            "uhubctl -l {} -p {} -a on > /dev/null".format(
                self.uhub_location, self.device_port
            )
        )
        self.wait(3)

    def power_off(self):
        self.now()
        print("[hardware/usb] Turning power off...")
        os.system(
            "uhubctl -l {} -p {} -r 100 -a off > /dev/null".format(
                self.uhub_location, self.device_port
            )
        )
        self.wait(3)

    def touch(self, location, action):
        raise NotImplementedError

    @staticmethod
    def wait(seconds):
        Device.now()
        print("[software] Waiting for {} seconds...".format(seconds))
        time.sleep(seconds)

    @staticmethod
    def now():
        print("\n[timestamp] {}".format(datetime.datetime.now()))
