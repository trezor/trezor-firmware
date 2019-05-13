from trezor import loop, ui


class Popup(ui.Layout):
    def __init__(self, content, time_ms=0):
        self.content = content
        self.time_ms = time_ms

    def dispatch(self, event, x, y):
        self.content.dispatch(event, x, y)

    def create_tasks(self):
        return self.handle_input(), self.handle_rendering(), self.handle_timeout()

    def handle_timeout(self):
        yield loop.sleep(self.time_ms * 1000)
        raise ui.Result(None)
