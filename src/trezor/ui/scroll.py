from . import display
from trezor import ui, loop, res


class Scroll():

    def __init__(self, page=0, totale_lines=0, lines_per_page=4):
        self.page = page
        self.totale_lines = totale_lines
        self.lines_per_page = lines_per_page

    def render(self):
        count = len(self.totale_lines) // self.lines_per_page
        padding = 20
        screen_height = const(220)
        cursor = 8
        
        if count * padding > screen_height:
            padding = screen_height // count

        x = 220
        y = (10 + (screen_height // 2)) - ((count // 2) * padding)

        for i in range(0, count):
            if (i != self.page):
                ui.display.bar(x, y + i * padding, cursor, cursor, ui.GREY)
            ui.display.bar(x, y + self.page * padding, cursor, cursor, ui.WHITE)

    def wait(self):
        while True:
            self.render()

