from . import consts

PIN_LOG_HALFWORDS = int(3 * (consts.WORD_SIZE / 2))


def expand_counter(c: int) -> int:
    c = ((c << 4) | c) & 0x0F0F
    c = ((c << 2) | c) & 0x3333
    c = ((c << 1) | c) & 0x5555
    c = ((c << 1) | c) ^ 0xAAAA
    return c


def compress_counter(c: int) -> int:
    c = c & 0x5555
    c = ((c >> 1) | c) & 0x3333
    c = ((c >> 2) | c) & 0x0F0F
    c = ((c >> 4) | c) & 0x00FF
    return c


class PinLogBlockwise:
    def __init__(self, norcow):
        self.norcow = norcow

    def init(self):
        self._write_log(0)

    def write_attempt(self):
        self._write_log(self.get_failures_count() + 1)

    def write_success(self):
        self._write_log(0)

    def get_failures_count(self) -> int:
        return self._get_logs()

    def _get_logs(self) -> int:
        logs = self.norcow.get(consts.PIN_LOG_KEY)

        if logs is None:
            raise ValueError("No PIN logs")

        ctr = int.from_bytes(logs[:2], "little")

        fails = compress_counter(ctr)

        for i in range(2, PIN_LOG_HALFWORDS, 2):
            if fails != compress_counter(int.from_bytes(logs[i : i + 2], "little")):
                raise ValueError("PIN logs corrupted")

        return fails

    def _write_log(self, fails: int):
        ctr = expand_counter(fails)
        data = ctr.to_bytes(2, "little")
        for _ in range(1, PIN_LOG_HALFWORDS):
            data += ctr.to_bytes(2, "little")
        self.norcow.set(consts.PIN_LOG_KEY, data)
