from typing import *


# extmod/modtrezorio/modtrezorio-fatfs.h
class FatFSFile:
    """
    Class encapsulating file
    """

    def __enter__(self) -> FatFSFile:
        """
        Return an open file object
        """
    from types import TracebackType

    def __exit__(
        self, type: Optional[Type[BaseException]],
        value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        """
        Close an open file object
        """

    def close(self) -> None:
        """
        Close an open file object
        """

    def read(self, data: bytearray) -> int:
        """
        Read data from the file
        """

    def write(self, data: Union[bytes, bytearray]) -> int:
        """
        Write data to the file
        """

    def seek(self, offset: int) -> None:
        """
        Move file pointer of the file object
        """

    def truncate(self) -> None:
        """
        Truncate the file
        """

    def sync(self) -> None:
        """
        Flush cached data of the writing file
        """


# extmod/modtrezorio/modtrezorio-fatfs.h
class FatFSDir(Iterator[Tuple[int, str, str]]):
    """
    Class encapsulating directory
    """

    def __next__(self) -> Tuple[int, str, str]:
        """
        Read an entry in the directory
        """


# extmod/modtrezorio/modtrezorio-fatfs.h
class FatFS:
    """
    Class encapsulating FAT filesystem
    """

    def __init__(self) -> None:
        """
        """

    def open(self, path: str, flags: str) -> FatFSFile:
        """
        Open or create a file
        """

    def listdir(self, path: str) -> FatFSDir:
        """
        List a directory (return generator)
        """

    def mkdir(self, path: str, exist_ok: bool=False) -> None:
        """
        Create a sub directory
        """

    def unlink(self, path: str) -> None:
        """
        Delete an existing file or directory
        """

    def stat(self, path: str) -> Tuple[int, str, str]:
        """
        Get file status
        """

    def rename(self, oldpath: str, newpath: str) -> None:
        """
        Rename/Move a file or directory
        """

    def mount(self) -> None:
        """
        Mount/Unmount a logical drive
        """

    def unmount(self) -> None:
        """
        Unmount a logical drive
        """

    def mkfs(self) -> None:
        """
        Create a FAT volume
        """


# extmod/modtrezorio/modtrezorio-flash.h
class FlashOTP:
    """
    """

    def __init__(self) -> None:
        """
        """

    def write(self, block: int, offset: int, data: bytes) -> None:
        """
        Writes data to OTP flash
        """

    def read(self, block: int, offset: int, data: bytearray) -> None:
        """
        Reads data from OTP flash
        """

    def lock(self, block: int) -> None:
        """
        Lock OTP flash block
        """

    def is_locked(self, block: int) -> bool:
        """
        Is OTP flash block locked?
        """


# extmod/modtrezorio/modtrezorio-hid.h
class HID:
    """
    USB HID interface configuration.
    """

    def __init__(
        self,
        iface_num: int,
        ep_in: int,
        ep_out: int,
        report_desc: bytes,
        subclass: int = 0,
        protocol: int = 0,
        polling_interval: int = 1,
        max_packet_len: int = 64,
    ) -> None:
        """
        """

    def iface_num(self) -> int:
        """
        Returns the configured number of this interface.
        """

    def write(self, msg: bytes) -> int:
        """
        Sends message using USB HID (device) or UDP (emulator).
        """

    def write_blocking(self, msg: bytes, timeout_ms: int) -> int:
        """
        Sends message using USB HID (device) or UDP (emulator).
        """


# extmod/modtrezorio/modtrezorio-poll.h
def poll(ifaces: Iterable[int], list_ref: List, timeout_us: int) -> bool:
    """
    Wait until one of `ifaces` is ready to read or write (using masks
    `list_ref`:
    `list_ref[0]` - the interface number, including the mask
    `list_ref[1]` - for touch event, tuple of:
                    (event_type, x_position, y_position)
                  - for USB read event, received bytes
    If timeout occurs, False is returned, True otherwise.
    """


# extmod/modtrezorio/modtrezorio-sbu.h
class SBU:
    """
    """

    def __init__(self) -> None:
        """
        """

    def set(self, sbu1: bool, sbu2: bool) -> None:
        """
        Sets SBU wires to sbu1 and sbu2 values respectively
        """


# extmod/modtrezorio/modtrezorio-sdcard.h
class SDCard:
    """
    """

    def __init__(self) -> None:
        """
        """

    def present(self) -> bool:
        """
        Returns True if SD card is detected, False otherwise.
        """

    def power(self, state: bool) -> bool:
        """
        Power on or power off the SD card interface.
        Returns True if in case of success, False otherwise.
        """

    def capacity(self) -> int:
        """
        Returns capacity of the SD card in bytes, or zero if not present.
        """

    def read(self, block_num: int, buf: bytearray) -> None:
        """
        Reads blocks starting with block_num from the SD card into buf.
        Number of bytes read is length of buf rounded down to multiply of
        SDCARD_BLOCK_SIZE. Returns True if in case of success, False otherwise.
        """

    def write(self, block_num: int, buf: bytes) -> None:
        """
        Writes blocks starting with block_num from buf to the SD card.
        Number of bytes written is length of buf rounded down to multiply of
        SDCARD_BLOCK_SIZE. Returns True if in case of success, False otherwise.
        """


# extmod/modtrezorio/modtrezorio-usb.h
class USB:
    """
    USB device configuration.
    """

    def __init__(
        self,
        vendor_id: int,
        product_id: int,
        release_num: int,
        device_class: int = 0,
        device_subclass: int = 0,
        device_protocol: int = 0,
        manufacturer: str = "",
        product: str = "",
        serial_number: str = "",
        interface: str = "",
        usb21_enabled: bool = True,
        usb21_landing: bool = True,
    ) -> None:
        """
        """

    def add(self, iface: Union[HID, VCP, WebUSB]) -> None:
        """
        Registers passed interface into the USB stack.
        """

    def open(self) -> None:
        """
        Initializes the USB stack.
        """

    def close(self) -> None:
        """
        Cleans up the USB stack.
        """


# extmod/modtrezorio/modtrezorio-vcp.h
class VCP:
    """
    USB VCP interface configuration.
    """

    def __init__(
        self,
        iface_num: int,
        data_iface_num: int,
        ep_in: int,
        ep_out: int,
        ep_cmd: int,
    ) -> None:
        """
        """

    def iface_num(self) -> int:
        """
        Returns the configured number of this interface.
        """


# extmod/modtrezorio/modtrezorio-webusb.h
class WebUSB:
    """
    USB WebUSB interface configuration.
    """

    def __init__(
        self,
        iface_num: int,
        ep_in: int,
        ep_out: int,
        subclass: int = 0,
        protocol: int = 0,
        polling_interval: int = 1,
        max_packet_len: int = 64,
    ) -> None:
        """
        """

    def iface_num(self) -> int:
        """
        Returns the configured number of this interface.
        """

    def write(self, msg: bytes) -> int:
        """
        Sends message using USB WebUSB (device) or UDP (emulator).
        """
POLL_READ: int  # wait until interface is readable and return read data
POLL_WRITE: int  # wait until interface is writable
TOUCH: int  # interface id of the touch events
TOUCH_START: int  # event id of touch start event
TOUCH_MOVE: int  # event id of touch move event
TOUCH_END: int  # event id of touch end event
WireInterface = Union[HID, WebUSB]
