from .device import Device


class TrezorT(Device):
    def update_firmware(self, file=None):
        # reset to enter bootloader again
        self.power_off()
        self.power_on()

        if not file:
            raise ValueError(
                "Uploading production firmware will replace the bootloader, it is not allowed!"
            )

        self.wait(5)
        print("[software] Updating the firmware to {}".format(file))
        self.run_trezorctl("firmware-update -s -f {}".format(file))

        # after firmware-update finishes wait for reboot
        self.wait(15)
        self.check_version()
