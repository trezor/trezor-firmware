from trezorutils import halt

if not __debug__:
    halt("Debugging is disabled")

if __debug__:
    save_screen = False
    save_screen_directory = "."

    current_content: list[str] = [""] * 20
    current_content.clear()

    watch_layout_changes = False
    layout_watcher = 0

    reset_internal_entropy: bytes = b""
