from typing import *

# extmod/modtrezorio/modtrezorio-flash.h
class FlashOTP:
    '''
    '''

    def __init__(self) -> None:
        '''
        '''

    def FlashOTP.write(self, block: int, offset: int, data: bytes) -> None:
        '''
        Writes data to OTP flash
        '''

    def FlashOTP.read(self, block: int, offset: int, data: bytearray) -> None:
        '''
        Reads data from OTP flash
        '''

    def FlashOTP.lock(self, block: int) -> None:
        '''
        Lock OTP flash block
        '''

    def FlashOTP.is_locked(self, block: int) -> bool:
        '''
        Is OTP flash block locked?
        '''

# extmod/modtrezorio/modtrezorio-hid.h
class HID:
    '''
    USB HID interface configuration.
    '''

    def __init__(self,
                 iface_num: int,
                 ep_in: int,
                 ep_out: int,
                 report_desc: bytes,
                 subclass: int = 0,
                 protocol: int = 0,
                 polling_interval: int = 1,
                 max_packet_len: int = 64) -> None:
        '''
        '''

    def iface_num(self) -> int:
        '''
        Returns the configured number of this interface.
        '''

    def write(self, msg: bytes) -> int:
        '''
        Sends message using USB HID (device) or UDP (emulator).
        '''

# extmod/modtrezorio/modtrezorio-poll.h
def poll(ifaces: Iterable[int], list_ref: List, timeout_us: int) -> bool:
    '''
    Wait until one of `ifaces` is ready to read or write (using masks
    `list_ref`:
    `list_ref[0]` - the interface number, including the mask
    `list_ref[1]` - for touch event, tuple of (event_type, x_position, y_position)
                  - for USB read event, received bytes
    If timeout occurs, False is returned, True otherwise.
    '''

# extmod/modtrezorio/modtrezorio-sbu.h
class SBU:
    '''
    '''

    def __init__(self) -> None:
        '''
        '''

    def set(self, sbu1: bool, sbu2: bool) -> None:
        '''
        Sets SBU wires to sbu1 and sbu2 values respectively
        '''

# extmod/modtrezorio/modtrezorio-sdcard.h
class SDCard:
    '''
    '''

    def __init__(self) -> None:
        '''
        '''

    def present(self) -> bool:
        '''
        Returns True if SD card is detected, False otherwise.
        '''

    def power(self, state: bool) -> bool:
        '''
        Power on or power off the SD card interface.
        Returns True if in case of success, False otherwise.
        '''

    def capacity(self) -> int:
        '''
        Returns capacity of the SD card in bytes, or zero if not present.
        '''

    def read(self, block_num: int, buf: bytearray) -> bool:
        '''
        Reads blocks starting with block_num from the SD card into buf.
        Number of bytes read is length of buf rounded down to multiply of SDCARD_BLOCK_SIZE.
        Returns True if in case of success, False otherwise.
        '''

    def write(self, block_num: int, buf: bytes) -> bool:
        '''
        Writes blocks starting with block_num from buf to the SD card.
        Number of bytes written is length of buf rounded down to multiply of SDCARD_BLOCK_SIZE.
        Returns True if in case of success, False otherwise.
        '''

# extmod/modtrezorio/modtrezorio-usb.h
class USB:
    '''
    USB device configuration.
    '''

    def __init__(self,
                 device_class: int=0,
                 device_subclass: int=0,
                 device_protocol: int=0,
                 vendor_id: int,
                 product_id: int,
                 release_num: int,
                 manufacturer: str='',
                 product: str='',
                 serial_number: str='',
                 interface: str='',
                 usb21_enabled: bool=True) -> None:
        '''
        '''

    def add(self, iface: Union[HID, VCP, WebUSB]) -> None:
        '''
        Registers passed interface into the USB stack.
        '''

    def open(self) -> None:
        '''
        Initializes the USB stack.
        '''

    def close(self) -> None:
        '''
        Cleans up the USB stack.
        '''

# extmod/modtrezorio/modtrezorio-vcp.h
class VCP:
    '''
    USB VCP interface configuration.
    '''

    def __init__(self,
                 iface_num: int,
                 data_iface_num: int,
                 ep_in: int,
                 ep_out: int,
                 ep_cmd: int) -> None:
        '''
        '''

    def iface_num(self) -> int:
        '''
        Returns the configured number of this interface.
        '''

# extmod/modtrezorio/modtrezorio-webusb.h
class WebUSB:
    '''
    USB WebUSB interface configuration.
    '''

    def __init__(self,
                 iface_num: int,
                 ep_in: int,
                 ep_out: int,
                 subclass: int = 0,
                 protocol: int = 0,
                 polling_interval: int = 1,
                 max_packet_len: int = 64) -> None:
        '''
        '''

    def iface_num(self) -> int:
        '''
        Returns the configured number of this interface.
        '''

    def write(self, msg: bytes) -> int:
        '''
        Sends message using USB WebUSB (device) or UDP (emulator).
        '''
