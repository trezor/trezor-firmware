from trezor import ui


class Container(ui.Component):
    def __init__(self, *children: ui.Component):
        self.children = children

    def dispatch(self, event: int, x: int, y: int) -> None:
        for child in self.children:
            child.dispatch(event, x, y)
