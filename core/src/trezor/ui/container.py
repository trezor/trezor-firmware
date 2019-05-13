from trezor import ui


class Container(ui.Control):
    def __init__(self, *children):
        self.children = children

    def dispatch(self, event, x, y):
        for child in self.children:
            child.dispatch(event, x, y)
