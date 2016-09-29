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
        waiter = loop.Wait([changer, renderer])
        result = await waiter
        if changer in waiter.finished:
            page = result
        else:
            return result


async def animate_swipe():
    await ui.animate_pulse(render_swipe_icon, ui.GREY, ui.DARK_GREY, speed=300000, delay=200000)


def render_swipe_icon(fg):
    ui.display.bar(102, 214, 36, 4, fg, ui.BLACK, 2)
    ui.display.bar(106, 222, 28, 4, fg, ui.BLACK, 2)
    ui.display.bar(110, 230, 20, 4, fg, ui.BLACK, 2)


def render_scrollbar(page, page_count):
    screen_height = const(220)
    size = const(10)

    padding = 18
    if page_count * padding > screen_height:
        padding = screen_height // page_count

    x = const(225)
    y = (screen_height // 2) - (page_count // 2) * padding

    for i in range(0, page_count):
        if i != page:
            ui.display.bar(x, y + i * padding, size,
                           size, ui.DARK_GREY, ui.BLACK, 4)
    ui.display.bar(x, y + page * padding, size, size, ui.WHITE, ui.BLACK, 4)
