
# extmod/modtrezormsg/modtrezormsg.c
def set_interfaces(ifaces: list/tuple) -> None:
    '''
    Configures USB interfaces with a list/tuple of (usage_page, ...)
    '''

# extmod/modtrezormsg/modtrezormsg.c
def get_interfaces() -> tuple:
    '''
    Reads a tuple (of usage pages) of configured USB interfaces
    '''

# extmod/modtrezormsg/modtrezormsg.c
def send(usage_page: int, message: bytes) -> int:
    '''
    Sends message using USB HID (device) or UDP (emulator).
    '''

# extmod/modtrezormsg/modtrezormsg.c
def select(timeout_us: int) -> tuple:
    '''
    Polls the event queue and returns the event object.
    Function returns None if timeout specified in microseconds is reached.
    '''
