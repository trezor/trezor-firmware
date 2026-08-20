import os
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
    def usb_reset(self, path):
        """Reset USB on the single device at `path`, if it is on the bus."""
        import usb1

        from trezorlib.models import ALL_MODELS
        from trezorlib.transport.webusb import WebUsbTransport, dev_to_str

        if path is None:
            self.log("[hardware/usb] No target device known, skipping USB reset")
            return

        # Not `WebUsbTransport.enumerate(usb_reset=True)`: that resets every
        # Trezor the process can see, and it reads a string descriptor per
        # device, which raises for the very device we are trying to recover.
        # Match on bus/port instead, skipping devices that cannot answer.
        usb_ids = {id for model in ALL_MODELS for id in model.usb_ids}
        done = False
        with usb1.USBContext() as ctx:
            for dev in ctx.getDeviceIterator(skip_on_error=True):
                try:
                    if (dev.getVendorID(), dev.getProductID()) not in usb_ids:
                        continue
                    if f"{WebUsbTransport.PATH_PREFIX}:{dev_to_str(dev)}" != path:
                        continue
                    self.log(f"[hardware/usb] Resetting {path}...")
                    handle = dev.open()
                    try:
                        handle.resetDevice()
                    finally:
                        handle.close()
                    done = True
                except Exception as e:
                    # Opening can fail on a device this broken
                    self.log(f"[hardware/usb] USB reset failed: {e}")
                    done = True
        if not done:
            self.log(f"[hardware/usb] {path} is not on the bus, nothing to reset")

    def wait_until_debuggable(self, timeout: int = 90, stable_for: int = 3):
        """Wait until a debuggable device has been up continuously for a while."""
        from trezorlib.transport.webusb import WebUsbTransport

        self.now()
        self.log(
            f"[software] Waiting up to {timeout}s for a debuggable device"
            f" to stay up for {stable_for}s..."
        )
        # The variable pytest honours too, so pinning it in the workflow scopes
        # the harness and the tests to the same device.
        target = os.environ.get("TREZOR_PATH") or None
        if target:
            self.log(f"[software] Restricting to TREZOR_PATH={target}")

        deadline = time.time() + timeout
        stable_path = None
        stable_since = None
        last_path = target
        reset_tried = False
        while True:
            try:
                found = [
                    t for t in WebUsbTransport.enumerate() if _is_debuggable(t.device)
                ]
                if target:
                    found = [t for t in found if t.get_path() == target]
                reason = f"{len(found)} debuggable devices"
            except Exception as e:
                # A device that is re-enumerating makes the whole WebUSB
                # enumeration raise, e.g. LIBUSB_ERROR_IO from getProduct()
                found, reason = [], f"enumeration failed: {e}"

            if len(found) == 1:
                path = found[0].get_path()
                last_path = path
                if stable_since is None or path != stable_path:
                    stable_since = time.time()
                    stable_path = path
                    self.log(f"[software] Debuggable device seen at {path}")
                elif time.time() - stable_since >= stable_for:
                    self.log(f"[software] Device is up and stable: {path}")
                    return path
            elif stable_since is not None:
                self.log(
                    f"[software] Device went away again ({reason}), restarting wait"
                )
                stable_path = None
                stable_since = None

            if time.time() >= deadline:
                if not reset_tried:
                    # Last resort: the device may be wedged rather than busy
                    # booting, in which case a USB reset can bring it back.
                    reset_tried = True
                    self.log(f"[software] Gave up waiting ({reason})")
                    stable_path = None
                    stable_since = None
                    self.usb_reset(last_path)
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

        # THP gets stuck on get-features, and on `list` too, since that opens
        # the device to read its name. Enumeration is all we can check there -
        # but without it a device that fails to boot is only noticed by pytest,
        # where it reads as a test failure rather than a flashing failure.
        if model_name != "Safe 7":
            print(self.check_model(model_name))
        else:
            print(self.check_enumerated())
