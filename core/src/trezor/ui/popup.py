from trezor import loop, ui, utils


class Popup(ui.Layout):
    def __init__(self, content: ui.Component, time_ms: int = 0) -> None:
        super().__init__()
        self.content = content
        if utils.DISABLE_ANIMATION:
            self.time_ms = 0
        else:
            self.time_ms = time_ms

    def dispatch(self, event: int, x: int, y: int) -> None:
        self.content.dispatch(event, x, y)

    def create_tasks(self) -> tuple[loop.Task, ...]:
        return self.handle_input(), self.handle_rendering(), self.handle_timeout()

    def handle_timeout(self) -> loop.Task:  # type: ignore
        yield loop.sleep(self.time_ms)
        raise ui.Result(None)
