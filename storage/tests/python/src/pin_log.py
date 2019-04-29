from . import consts, helpers, prng


class PinLog:
    def __init__(self, norcow):
        self.norcow = norcow

    def init(self):
        guard_key = self._generate_guard_key()
        guard_mask, guard = self.derive_guard_mask_and_value(guard_key)

        pin_success_log = (~guard_mask & consts.ALL_FF_LOG) | guard
        pin_entry_log = (~guard_mask & consts.ALL_FF_LOG) | guard
        self._write_log(guard_key, pin_success_log, pin_entry_log)

    def derive_guard_mask_and_value(self, guard_key: int) -> (int, int):
        if guard_key > 0xFFFFFFFF:
            raise ValueError("Invalid guard key")

        guard_mask = ((guard_key & consts.LOW_MASK) << 1) | (
            (~guard_key & 0xFFFFFFFF) & consts.LOW_MASK
        )
        guard = (((guard_key & consts.LOW_MASK) << 1) & guard_key) | (
            ((~guard_key & 0xFFFFFFFF) & consts.LOW_MASK) & (guard_key >> 1)
        )
        return helpers.expand_to_log_size(guard_mask), helpers.expand_to_log_size(guard)

    def write_attempt(self):
        guard_key, pin_success_log, pin_entry_log = self._get_logs()
        guard_mask, guard = self.derive_guard_mask_and_value(guard_key)
        assert (pin_entry_log & guard_mask) == guard

        clean_pin_entry_log = self.remove_guard_bits(guard_mask, pin_entry_log)
        clean_pin_entry_log = clean_pin_entry_log >> 2  # set 11 to 00
        pin_entry_log = (
            clean_pin_entry_log & (~guard_mask & consts.ALL_FF_LOG)
        ) | guard

        self._write_log(guard_key, pin_success_log, pin_entry_log)

    def write_success(self):
        guard_key, pin_success_log, pin_entry_log = self._get_logs()
        pin_success_log = pin_entry_log

        self._write_log(guard_key, pin_success_log, pin_entry_log)

    def get_failures_count(self) -> int:
        guard_key, pin_succes_log, pin_entry_log = self._get_logs()
        guard_mask, _ = self.derive_guard_mask_and_value(guard_key)

        pin_succes_log = self.remove_guard_bits(guard_mask, pin_succes_log)
        pin_entry_log = self.remove_guard_bits(guard_mask, pin_entry_log)

        # divide by two because bits are doubled after remove_guard_bits()
        return bin(pin_succes_log - pin_entry_log).count("1") // 2

    def remove_guard_bits(self, guard_mask: int, log: int) -> int:
        """
        Removes all guard bits and replaces each guard bit
        with its neighbour value.
        Example: 0g0gg1 -> 000011
        """
        log = log & (~guard_mask & consts.ALL_FF_LOG)
        log = ((log >> 1) | log) & helpers.expand_to_log_size(consts.LOW_MASK)
        log = log | (log << 1)
        return log

    def _generate_guard_key(self) -> int:
        while True:
            r = prng.random_uniform(consts.GUARD_KEY_RANDOM_MAX)
            r = (r * consts.GUARD_KEY_MODULUS + consts.GUARD_KEY_REMAINDER) & 0xFFFFFFFF
            if self._check_guard_key(r):
                return r

    def _check_guard_key(self, guard_key: int) -> bool:
        """
        Checks if guard_key is congruent to 15 modulo 6311 and
        some other conditions, see the docs.
        """
        count = (guard_key & 0x22222222) + ((guard_key >> 2) & 0x22222222)
        count = count + (count >> 4)

        zero_runs = ~guard_key & 0xFFFFFFFF
        zero_runs = zero_runs & (zero_runs >> 2)
        zero_runs = zero_runs & (zero_runs >> 1)
        zero_runs = zero_runs & (zero_runs >> 1)
        one_runs = guard_key
        one_runs = one_runs & (one_runs >> 2)
        one_runs = one_runs & (one_runs >> 1)
        one_runs = one_runs & (one_runs >> 1)

        return (
            ((count & 0x0E0E0E0E) == 0x04040404)
            & (one_runs == 0)
            & (zero_runs == 0)
            & (guard_key % consts.GUARD_KEY_MODULUS == consts.GUARD_KEY_REMAINDER)
        )

    def _get_logs(self) -> (int, int, int):
        pin_log = self.norcow.get(consts.PIN_LOG_KEY)
        guard_key = pin_log[: consts.PIN_LOG_GUARD_KEY_SIZE]
        guard_key = helpers.word_to_int(guard_key)
        guard_mask, guard = self.derive_guard_mask_and_value(guard_key)
        pin_entry_log = pin_log[consts.PIN_LOG_GUARD_KEY_SIZE + consts.PIN_LOG_SIZE :]
        pin_entry_log = helpers.to_int_by_words(pin_entry_log)
        pin_success_log = pin_log[
            consts.PIN_LOG_GUARD_KEY_SIZE : consts.PIN_LOG_GUARD_KEY_SIZE
            + consts.PIN_LOG_SIZE
        ]
        pin_success_log = helpers.to_int_by_words(pin_success_log)

        return guard_key, pin_success_log, pin_entry_log

    def _write_log(self, guard_key: int, pin_success_log: int, pin_entry_log: int):
        pin_log = (
            helpers.int_to_word(guard_key)
            + helpers.to_bytes_by_words(pin_success_log, consts.PIN_LOG_SIZE)
            + helpers.to_bytes_by_words(pin_entry_log, consts.PIN_LOG_SIZE)
        )
        try:
            self.norcow.replace(consts.PIN_LOG_KEY, pin_log)
        except RuntimeError:
            self.norcow.set(consts.PIN_LOG_KEY, pin_log)
