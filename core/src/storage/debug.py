from trezorutils import EMULATOR, halt

if not __debug__:
    halt("Debugging is disabled")

if __debug__:
    save_screen = False
    if EMULATOR:
        refresh_index = 0
        save_screen_directory = bytearray(4096)
        save_screen_directory[:] = b"."

    layout_watcher = False

    reset_internal_entropy = bytearray(32)
    reset_internal_entropy[:] = b""

    # Cache pin to allow unlocking (for THP pairing)
    _pin_cache = bytearray(50)
    _pin_cache[:] = b""

    def set_pin(pin: str | None) -> None:
        _pin_cache[:] = (pin or "").encode()

    def get_pin() -> str | None:
        if not _pin_cache:
            return None

        return _pin_cache.decode()
