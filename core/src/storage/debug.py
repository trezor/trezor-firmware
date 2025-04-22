from trezorutils import EMULATOR, halt

if not __debug__:
    halt("Debugging is disabled")

if __debug__:
    save_screen = False
    if EMULATOR:
        save_screen_directory = bytearray(4096)
        save_screen_directory[:] = b"."

    layout_watcher = False

    reset_internal_entropy = bytearray(32)
    reset_internal_entropy[:] = bytes()
