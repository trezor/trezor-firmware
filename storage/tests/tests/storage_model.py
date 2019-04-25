# Logical storage model used for testing.


class StorageModel:
    _EMPTY_PIN = 1
    _PIN_MAX_TRIES = 16

    def __init__(self) -> None:
        self.wipe()

    def init(self, salt: bytes) -> None:
        self.unlocked = False

    def wipe(self) -> None:
        self.unlocked = False
        self.pin = 1
        self.pin_rem = self._PIN_MAX_TRIES
        self.dict = {}

    def lock(self) -> None:
        self.unlocked = False

    def unlock(self, pin: int) -> bool:
        if pin == self.pin:
            self.pin_rem = self._PIN_MAX_TRIES
            self.unlocked = True
            return True
        else:
            self.pin_rem -= 1
            if self.pin_rem <= 0:
                self.wipe()
            return False

    def has_pin(self) -> bool:
        return self.pin != self._EMPTY_PIN

    def get_pin_rem(self) -> int:
        return self.pin_rem

    def change_pin(self, oldpin: int, newpin: int) -> bool:
        if self.unlocked and self.unlock(oldpin):
            self.pin = newpin
            return True
        else:
            return False

    def get(self, key: int) -> bytes:
        if (key & 0x8000 != 0 or self.unlocked) and self.dict.get(key) is not None:
            return self.dict[key]
        raise RuntimeError("Failed to find key in storage.")

    def set(self, key: int, val: bytes) -> None:
        if self.unlocked:
            self.dict[key] = val
        else:
            raise RuntimeError("Failed to set value in storage.")

    def delete(self, key: int) -> bool:
        if not self.unlocked:
            return False
        try:
            self.dict.pop(key)
        except KeyError:
            return False
        return True

    def __iter__(self):
        return iter(self.dict.items())
