
# ../extmod/modtrezormsg/modtrezormsg.c
def setup(ifaces: list) -> None:
    '''
    Configures USB interfaces with a list of tuples (interface_number, usage_page)
    '''

# ../extmod/modtrezormsg/modtrezormsg.c
def send(iface: int, message: bytes) -> int:
    '''
    Sends message using USB HID (device) or UDP (emulator).
    '''

# ../extmod/modtrezormsg/modtrezormsg.c
def select(timeout_us: int) -> tuple:
    '''
    Polls the event queue and returns the event object.
    Function returns None if timeout specified in microseconds is reached.
    '''
