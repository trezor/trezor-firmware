from micropython import const
from trezor import loop, ui
from .swipe import Swipe, SWIPE_UP, SWIPE_DOWN


async def change_page(page, page_count):
    while True:
        s = await Swipe()
        if s == SWIPE_UP and page < page_count - 1:
            return page + 1  # scroll down
        elif s == SWIPE_DOWN and page > 0:
            return page - 1  # scroll up


async def paginate(render_page, page_count, page=0, *args):
    while True:
        changer = change_page(page, page_count)
        renderer = render_page(page, page_count, *args)
        waiter = loop.wait(changer, renderer)
        result = await waiter
        if changer in waiter.finished:
            page = result
        else:
            return result


async def animate_swipe():
    time_delay = const(30000)
    draw_delay = const(200000)

    sleep = loop.sleep(time_delay)
    for t in ui.pulse(draw_delay):
        fg = ui.blend(ui.GREY, ui.DARK_GREY, t)
        ui.display.bar_radius(102, 214, 36, 4, fg, ui.BLACK, 2)
        ui.display.bar_radius(106, 222, 28, 4, fg, ui.BLACK, 2)
        ui.display.bar_radius(110, 230, 20, 4, fg, ui.BLACK, 2)
        await sleep


def render_scrollbar(page, page_count):
    bbox = const(220)
    size = const(10)

    padding = 18
    if page_count * padding > bbox:
        padding = bbox // page_count

    x = const(225)
    y = (bbox // 2) - (page_count // 2) * padding

    for i in range(0, page_count):
        if i != page:
            ui.display.bar_radius(x, y + i * padding, size,
                                  size, ui.DARK_GREY, ui.BLACK, 4)
    ui.display.bar_radius(x, y + page * padding, size,
                          size, ui.WHITE, ui.BLACK, 4)
