from trezor.ui import Widget


class Container(Widget):
    def __init__(self, *children):
        self.children = children

    def taint(self):
        super().taint()
        for child in self.children:
            child.taint()

    def render(self):
        for child in self.children:
            child.render()

    def touch(self, event, pos):
        for child in self.children:
            result = child.touch(event, pos)
            if result is not None:
                return result
