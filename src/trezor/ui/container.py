
class Container:

    def __init__(self, *children):
        self.children = children

    def render(self):
        for child in self.children:
            child.render()

    def send(self, event, pos):
        for child in self.children:
            result = child.send(event, pos)
            if result is not None:
                return result
