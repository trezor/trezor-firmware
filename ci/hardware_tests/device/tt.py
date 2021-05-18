from .device import Device


class TrezorT(Device):
    def update_firmware(self, file=None):
        if not file:
            raise ValueError(
                "Uploading production firmware will replace the bootloader, it is not allowed!"
            )

        # reset to enter bootloader again
        self.power_off()
        self.power_on()

        self.wait(5)
        self.check_model("Trezor T bootloader")

        self.run_trezorctl("device wipe --bootloader || true")
        self.wait(5)
        self.power_off()
        self.power_on()

        self.wait(5)
        self.log("[software] Updating the firmware to {}".format(file))
        self.run_trezorctl("firmware-update -s -f {}".format(file))

        # after firmware-update finishes wait for reboot
        self.wait(15)
        return self.check_model("Trezor T")
