from trezorutils import halt

if not __debug__:
    halt("Debugging is disabled")

if __debug__:
    layout_watcher = False

    reset_internal_entropy = bytearray(32)
    reset_internal_entropy[:] = bytes()
