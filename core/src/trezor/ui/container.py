from trezor import ui


class Container(ui.Component):
    def __init__(self, *children: ui.Component):
        super().__init__()
        self.children = children

    def dispatch(self, event: int, x: int, y: int) -> None:
        for child in self.children:
            child.dispatch(event, x, y)

    if __debug__:

        def read_content(self) -> list[str]:
            return sum((c.read_content() for c in self.children), [])
