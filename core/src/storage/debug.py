from trezorutils import halt

if not __debug__:
    halt("Debugging is disabled")

if __debug__:
    save_screen = False
    save_screen_directory = "."

    current_content_tokens: list[str] = [""] * 60
    current_content_tokens.clear()

    watch_layout_changes = False
    layout_watcher = 0

    reset_internal_entropy: bytes = b""

    class DebugEvents:
        def __init__(self):
            self.reset()

        def reset(self) -> None:
            self.last_event = 0
            self.last_result: int | None = None
            self.awaited_event: int | None = None

    debug_events = DebugEvents()

    def reset_debug_events() -> None:
        debug_events.reset()

    # Event resulted in the layout change, call
    # notify_layout_change with this ID in first_paint of next layout.
    new_layout_event_id: int | None = None
