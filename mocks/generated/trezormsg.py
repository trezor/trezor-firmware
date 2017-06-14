
# extmod/modtrezormsg/modtrezormsg.c
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

# extmod/modtrezormsg/modtrezormsg.c
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

# extmod/modtrezormsg/modtrezormsg.c
class USB:
    '''
    USB device configuration.
    '''

    def __init__(self,
                 vendor_id: int,
                 product_id: int,
                 release_num: int,
                 manufacturer_str: str,
                 product_str: str,
                 serial_number_str: str,
                 configuration_str: str = '',
                 interface_str: str = '') -> None:
        '''
        '''

# extmod/modtrezormsg/modtrezormsg.c
class Msg:
    '''
    Interface with USB and touch events.
    '''

    def __init__(self) -> None:
        '''
        '''

    def init_usb(self, usb_info: USB, usb_ifaces: List[Union[HID, VCP]]) -> None:
        '''
        Registers passed interfaces and initializes the USB stack.
        '''

    def deinit_usb(self) -> None:
        '''
        Cleans up the USB stack
        '''

    def send(self, iface: int, message: bytes) -> int:
        '''
        Sends message using USB HID (device) or UDP (emulator).
        '''

    def select(self, timeout_us: int) -> tuple:
        '''
        Polls the event queue and returns the event object.
        Function returns None if timeout specified in microseconds is reached.
        '''
