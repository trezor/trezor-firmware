from typing import *
from buffer_types import *


# upymod/modtrezorio/modtrezorio-ipc.h
def ipc_send(remote: int, fn: int, data: AnyBytes) -> None:
    """
    Sends an IPC message to the specified remote task.
    """


# upymod/modtrezorio/modtrezorio-ipc.h
class IpcMessage:
    """
    IPC message structure.
    """

    def fn(self) -> int:
        """
        Returns the function number.
        """

    def remote(self) -> int:
        """
        Returns the remote task ID.
        """

    def free(self) -> None:
        """
        Frees the IPC message resources.
        """

    def data(self) -> bytes:
        """
        Returns the IPC message data as bytes.
        """


# upymod/modtrezorio/modtrezorio-poll.h
def poll(ifaces: Iterable[int], list_ref: list, timeout_ms: int) -> bool:
    """
    Wait until one of `ifaces` is ready to read or write (using masks
    `io.POLL_READ` and `io.POLL_WRITE`) and assign the result into
    `list_ref`:

    - `list_ref[0]` - the interface number, including the mask
    - `list_ref[1]` - for touch event, tuple of:
                    (event_type, x_position, y_position)
                  - for button event (T1), tuple of:
                    (event type, button number)
                  - for USB read event, received bytes

    If timeout occurs, False is returned, True otherwise.
    """


# upymod/modtrezorio/modtrezorio-usb-if.h
class USBIF:
    """
    USB USBIF interface configuration.
    """

    def __init__(
        self,
        handle: int,
    ) -> None:
        """
        """

    def iface_num(self) -> int:
        """
        Returns the configured number of this interface.
        """

    def write(self, msg: AnyBytes) -> int:
        """
        Sends message using USB interface.
        """

    def write_blocking(self, msg: AnyBytes, timeout_ms: int) -> int:
        """
        Sends message using USB interface.
        """

    def read(self, buf: bytearray, offset: int = 0) -> int:
        """
        Reads message using USB interface
        """
    RX_PACKET_LEN: ClassVar[int]
    """Length of one USB RX packet."""
    TX_PACKET_LEN: ClassVar[int]
    """Length of one USB TX packet."""


# upymod/modtrezorio/modtrezorio-usb.h
class USB:
    """
    USB device configuration.
    """

    def __init__(
        self,
    ) -> None:
        """
        """

    def open(self, serial_number: str) -> None:
        """
        Initializes the USB stack.
        """

    def close(self) -> None:
        """
        Cleans up the USB stack.
        """
from . import fatfs, haptic, sdcard, ble, pm, rgb_led, ipc, app_cache
POLL_READ: int  # wait until interface is readable and return read data
POLL_WRITE: int  # wait until interface is writable

BLE: int  # interface id of the BLE events
BLE_EVENT: int # interface id for BLE events

PM_EVENT: int  # interface id for power manager events

IPC2_EVENT: int  # interface id for IPC2 events

TOUCH: int  # interface id of the touch events
TOUCH_START: int  # event id of touch start event
TOUCH_MOVE: int  # event id of touch move event
TOUCH_END: int  # event id of touch end event
BUTTON: int  # interface id of button events
BUTTON_PRESSED: int  # button down event
BUTTON_RELEASED: int  # button up event
BUTTON_LEFT: int  # button number of left button
BUTTON_RIGHT: int  # button number of right button
USB_EVENT: int # interface id for USB events
WireInterface = USBIF | BLEIF
USBIF_WIRE: int  # interface id of the USB wire interface
USBIF_DEBUG: int  # interface id of the USB debug interface
USBIF_WEBAUTHN: int  # interface id of the USB WebAuthn
