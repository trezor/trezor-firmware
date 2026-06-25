from .device import Device


class TrezorCore(Device):
    def update_firmware(self, file=None, model_name="Trezor T"):
        if not file:
            raise ValueError(
                "Uploading production firmware will replace the bootloader, it is not allowed!"
            )

        # reset to enter bootloader again
        self.power_off()
        self.wait(10)
        self.power_on()

        self.wait(20)
        self.check_model("bootloader")

        self.run_trezorctl("device wipe --bootloader || true")
        self.wait(10)
        self.power_off()
        self.power_on()

        self.wait(10)
        self.log(f"[software] Updating the firmware to {file}")
        self.run_trezorctl(f"firmware-update -s -f {file}")

        # after firmware-update finishes wait for reboot
        self.wait(30)

        # THP gets stuck on get-features
        if model_name != "Safe 7":
            print(self.check_model(model_name))
