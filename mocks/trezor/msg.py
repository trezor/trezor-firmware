
# extmod/modtrezormsg/modtrezormsg.c
def init_usb(usb_info, usb_ifaces) -> None:
    '''
    Registers passed interfaces and initializes the USB stack
    '''

# extmod/modtrezormsg/modtrezormsg.c
def deinit_usb() -> None:
    '''
    Cleans up the USB stack
    '''

# extmod/modtrezormsg/modtrezormsg.c
def send(iface: int, message: bytes) -> int:
    '''
    Sends message using USB HID (device) or UDP (emulator).
    '''

# extmod/modtrezormsg/modtrezormsg.c
def select(timeout_us: int) -> tuple:
    '''
    Polls the event queue and returns the event object.
    Function returns None if timeout specified in microseconds is reached.
    '''
