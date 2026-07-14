# complete code
import time
from trezor import utils

class PasswordCache:
    def __init__(self):
        self.cache = {}
        self.ttl = 10  # 10 seconds

    def expire(self):
        current_time = time.time()
        self.cache = {pin: result for pin, result in self.cache.items() if current_time - result['timestamp'] < self.ttl}

    def __setitem__(self, pin, result):
        self.cache[pin] = {'result': result, 'timestamp': time.time()}

    def __getitem__(self, pin):
        return self.cache[pin]['result']