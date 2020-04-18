from trezor import ui

if False:
    from typing import List


class Container(ui.Component):
    def __init__(self, *children: ui.Component):
        self.children = children

    def dispatch(self, event: int, x: int, y: int) -> None:
        for child in self.children:
            child.dispatch(event, x, y)

    if __debug__:

        def read_content(self) -> List[str]:
            return sum((c.read_content() for c in self.children), [])
