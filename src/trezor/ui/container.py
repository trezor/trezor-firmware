from trezor.ui import Widget


class Container(Widget):
    def __init__(self, *children):
        self.children = children

    def render(self):
        for child in self.children:
            child.render()

    def touch(self, event, pos):
        for child in self.children:
            result = child.touch(event, pos)
            if result is not None:
                return result
