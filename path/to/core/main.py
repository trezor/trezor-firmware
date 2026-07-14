# complete code
import time
from trezor import utils
from core.crypto.password import Password

class Trezor:
    def __init__(self):
        self.password = Password('')

    def unlock(self, pin):
        start_time = time.time()
        result = self.password.verify(pin)
        end_time = time.time()
        print(f'Unlock time: {end_time - start_time} seconds')
        return result