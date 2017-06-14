
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
        Reads block_num block from the SD card into buf.
        Returns True if in case of success, False otherwise.
        '''

    def write(self, block_num: int, buf: bytes) -> bool:
        '''
        Writes block_num block from buf to the SD card.
        Returns True if in case of success, False otherwise.
        '''
