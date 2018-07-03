from micropython import const

from trezor import loop, res, ui
from trezor.ui.swipe import SWIPE_DOWN, SWIPE_UP, SWIPE_VERTICAL, Swipe

if __debug__:
    from apps.debug import swipe_signal


async def change_page(page, page_count):
    while True:
        if page == 0:
            d = SWIPE_UP
        elif page == page_count - 1:
            d = SWIPE_DOWN
        else:
            d = SWIPE_VERTICAL
        swipe = Swipe(directions=d)
        if __debug__:
            s = await loop.spawn(swipe, swipe_signal)
        else:
            s = await swipe
        if s == SWIPE_UP:
            return page + 1  # scroll down
        elif s == SWIPE_DOWN:
            return page - 1  # scroll up


async def paginate(render_page, page_count, page=0, *args):
    while True:
        changer = change_page(page, page_count)
        renderer = render_page(page, page_count, *args)
        waiter = loop.spawn(changer, renderer)
        result = await waiter
        if changer in waiter.finished:
            page = result
        else:
            return result


async def animate_swipe():
    time_delay = const(40000)
    draw_delay = const(200000)

    ui.display.text_center(130, 220, "Swipe", ui.BOLD, ui.GREY, ui.BG)

    sleep = loop.sleep(time_delay)
    icon = res.load(ui.ICON_SWIPE)
    for t in ui.pulse(draw_delay):
        fg = ui.blend(ui.GREY, ui.DARK_GREY, t)
        ui.display.icon(70, 205, icon, fg, ui.BG)
        yield sleep


def render_scrollbar(page, page_count):
    bbox = const(220)
    size = const(8)

    padding = 14
    if page_count * padding > bbox:
        padding = bbox // page_count

    x = const(220)
    y = (bbox // 2) - (page_count // 2) * padding

    for i in range(0, page_count):
        if i != page:
            ui.display.bar_radius(x, y + i * padding, size, size, ui.GREY, ui.BG, 4)
    ui.display.bar_radius(x, y + page * padding, size, size, ui.FG, ui.BG, 4)


class Scrollpage(ui.Widget):
    def __init__(self, content, page, page_count):
        self.content = content
        self.page = page
        self.page_count = page_count

    def render(self):
        self.content.render()
        render_scrollbar(self.page, self.page_count)

    async def __iter__(self):
        return await loop.spawn(super().__iter__(), self.content)
