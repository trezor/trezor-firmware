import serial

from .device import Device


class TrezorOne(Device):
    def __init__(self, uhub_location, arduino_serial, device_port):
        super().__init__(uhub_location, device_port)
        self.serial = serial.Serial(arduino_serial, 9600)

    def touch(self, location, action):
        self.now()
        self.log(
            "[hardware/trezor] Touching the {} button by {}...".format(location, action)
        )
        self.serial.write(("{} {}\n".format(location, action)).encode())

    def update_firmware(self, file=None):
        if file:
            unofficial = True
            trezorctlcmd = "firmware-update -s -f {} &".format(file)
            self.log("[software] Updating the firmware to {}".format(file))
        else:
            unofficial = False
            trezorctlcmd = "firmware-update &"
            self.log("[software] Updating the firmware to latest")
        self.wait(3)
        self._enter_bootloader()

        self.wait(3)
        self.check_model("Trezor 1 bootloader")

        self.run_trezorctl(trezorctlcmd)
        self.wait(3)
        self.touch("right", "click")
        self.wait(25)
        if unofficial:
            self.touch("right", "click")
        self.wait(10)
        self.power_off()
        self.power_on()
        if unofficial:
            self.touch("right", "click")
            self.wait(5)
            self.touch("right", "click")
        self.wait(10)
        return self.check_model("Trezor 1")

    def _enter_bootloader(self):
        self.power_off()
        self.touch("all", "press")
        self.wait(2)
        self.power_on()
        self.wait(2)
        self.touch("all", "unpress")
