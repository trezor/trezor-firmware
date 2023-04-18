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

    class DebugEvents:
        def __init__(self):
            self.last_event = 0
            self.last_result: int | None = None
            self.awaited_event: int | None = None

    debug_events = DebugEvents()

    def reset_debug_events() -> None:
        global debug_events

        debug_events = DebugEvents()

    new_layout = False
    new_layout_timeout = False
