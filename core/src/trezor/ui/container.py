from trezor import ui


class Container(ui.Control):
    def __init__(self, *children: ui.Control):
        self.children = children

    def dispatch(self, event: int, x: int, y: int) -> None:
        for child in self.children:
            child.dispatch(event, x, y)
