import os

from .device import Device


class TrezorOne(Device):
    def touch(self, location, action):
        self.now()
        print(
            "[hardware/trezor] Touching the {} button by {}...".format(location, action)
        )
        self.serial.write(("{} {}\n".format(location, action)).encode())

    def update_firmware(self, file=None):
        if file:
            unofficial = True
            trezorctlcmd = "trezorctl firmware-update -s -f {} &".format(file)
            print("[software/trezorctl] Updating the firmware to {}...".format(file))
        else:
            unofficial = False
            trezorctlcmd = "trezorctl firmware-update &"
            print("[software/trezorctl] Updating the firmware to latest...")
        self.wait(3)
        self._enter_bootloader()

        self.wait(3)
        os.system(trezorctlcmd)
        self.wait(3)
        self.touch("right", "click")
        self.wait(20)
        if unofficial:
            self.touch("right", "click")
        self.wait(10)
        self.power_off()
        self.power_on()
        if unofficial:
            self.touch("right", "click")
            self.wait(5)
            self.touch("right", "click")
        self.wait(5)
        os.system("trezorctl get-features|grep version")

    def _enter_bootloader(self):
        self.power_off()
        self.touch("all", "press")
        self.wait(2)
        self.power_on()
        self.wait(2)
        self.touch("all", "unpress")
