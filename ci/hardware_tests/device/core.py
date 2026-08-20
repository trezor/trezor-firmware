import time

from .device import Device

# The debuglink interface only exists on a debug firmware build, so its presence
# also tells a booted firmware apart from the bootloader that just flashed it.
DEBUG_INTERFACE = 1


def _is_debuggable(dev) -> bool:
    """Whether the device exposes the debuglink interface."""
    import usb1

    try:
        return (
            dev[0][DEBUG_INTERFACE][0].getClass()
            == usb1.libusb1.LIBUSB_CLASS_VENDOR_SPEC
        )
    except Exception:
        # No such configuration/interface, or the device stopped answering
        return False


class TrezorCore(Device):
    def usb_reset(self):
        """Reset USB on devices stuck in a state where they answer nothing.

        The same operation as `trezorctl usb-reset`, which exists for exactly
        this: LIBUSB_ERROR_PIPE and friends from a device in a messed state.
        """
        from trezorlib.transport.webusb import WebUsbTransport

        self.log("[hardware/usb] Performing USB reset...")
        try:
            WebUsbTransport.enumerate(usb_reset=True)
        except Exception as e:
            # Resetting needs to open the device, which is itself allowed to
            # fail on a device this broken.
            self.log(f"[hardware/usb] USB reset failed: {e}")

    def wait_until_debuggable(self, timeout: int = 90, stable_for: int = 3):
        """Wait until a debuggable device has been up continuously for a while."""
        from trezorlib.transport.webusb import WebUsbTransport

        self.now()
        self.log(
            f"[software] Waiting up to {timeout}s for a debuggable device"
            f" to stay up for {stable_for}s..."
        )
        deadline = time.time() + timeout
        stable_since = None
        reset_tried = False
        while True:
            try:
                found = [
                    t for t in WebUsbTransport.enumerate() if _is_debuggable(t.device)
                ]
                reason = f"{len(found)} debuggable devices"
            except Exception as e:
                # A device that is re-enumerating makes the whole WebUSB
                # enumeration raise, e.g. LIBUSB_ERROR_IO from getProduct()
                found, reason = [], f"enumeration failed: {e}"

            if len(found) == 1:
                if stable_since is None:
                    stable_since = time.time()
                    self.log(
                        f"[software] Debuggable device seen at {found[0].get_path()}"
                    )
                elif time.time() - stable_since >= stable_for:
                    path = found[0].get_path()
                    self.log(f"[software] Device is up and stable: {path}")
                    return path
            elif stable_since is not None:
                self.log(
                    f"[software] Device went away again ({reason}), restarting wait"
                )
                stable_since = None

            if time.time() >= deadline:
                if not reset_tried:
                    # Last resort: the device may be wedged rather than busy
                    # booting, in which case a USB reset can bring it back.
                    reset_tried = True
                    self.log(f"[software] Gave up waiting ({reason})")
                    self.usb_reset()
                    deadline = time.time() + timeout
                    continue
                raise RuntimeError(
                    f"no single debuggable device after {timeout}s ({reason})"
                )
            time.sleep(1)

    def update_firmware(self, file=None, model_name="Trezor T"):
        if not file:
            raise ValueError(
                "Uploading production firmware will replace the bootloader, it is not allowed!"
            )

        # reset to enter bootloader again
        self.power_off()
        self.wait(5)
        self.power_on()

        self.wait(10)
        self.check_model("bootloader")

        self.run_trezorctl("device wipe --bootloader || true")
        self.wait(5)
        self.power_off()
        self.power_on()

        self.wait(5)
        self.log(f"[software] Updating the firmware to {file}")
        self.run_trezorctl(f"firmware-update -s -f {file}")

        # After firmware-update finishes, the bootloader still has to verify
        # the image and jump into it, so wait for the firmware itself to come
        # up rather than for whatever is on the bus right now.
        self.wait_until_debuggable()

        # THP gets stuck on get-features
        if model_name != "Safe 7":
            print(self.check_model(model_name))
