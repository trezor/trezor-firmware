from micropython import const

from trezor import loop, res, ui, utils

from .button import Button, ButtonCancel, ButtonConfirm, ButtonDefault
from .confirm import CANCELLED, CONFIRMED, Confirm
from .swipe import SWIPE_DOWN, SWIPE_UP, SWIPE_VERTICAL, Swipe
from .text import TEXT_MAX_LINES, Span, Text

_PAGINATED_LINE_WIDTH = const(204)


def render_scrollbar(pages: int, page: int) -> None:
    BBOX = const(220)
    SIZE = const(8)

    padding = 14
    if pages * padding > BBOX:
        padding = BBOX // pages

    X = const(220)
    Y = (BBOX // 2) - (pages // 2) * padding

    for i in range(0, pages):
        if i == page:
            fg = ui.FG
        else:
            fg = ui.GREY
        ui.display.bar_radius(X, Y + i * padding, SIZE, SIZE, fg, ui.BG, 4)


def render_swipe_icon() -> None:
    if utils.DISABLE_ANIMATION:
        c = ui.GREY
    else:
        PULSE_PERIOD = const(1_200_000)
        t = ui.pulse(PULSE_PERIOD)
        c = ui.blend(ui.GREY, ui.DARK_GREY, t)

    icon = res.load(ui.ICON_SWIPE)
    ui.display.icon(70, 205, icon, c, ui.BG)


def render_swipe_text() -> None:
    ui.display.text_center(130, 220, "Swipe", ui.BOLD, ui.GREY, ui.BG)


class Paginated(ui.Layout):
    def __init__(
        self, pages: list[ui.Component], page: int = 0, one_by_one: bool = False
    ):
        super().__init__()
        self.pages = pages
        self.page = page
        self.one_by_one = one_by_one

    def dispatch(self, event: int, x: int, y: int) -> None:
        pages = self.pages
        page = self.page
        pages[page].dispatch(event, x, y)

        if event is ui.RENDER:
            length = len(pages)
            if page < length - 1:
                render_swipe_icon()
                if self.repaint:
                    render_swipe_text()
            if self.repaint:
                render_scrollbar(length, page)
                self.repaint = False

    async def handle_paging(self) -> None:
        if self.page == 0:
            directions = SWIPE_UP
        elif self.page == len(self.pages) - 1:
            directions = SWIPE_DOWN
        else:
            directions = SWIPE_VERTICAL

        if __debug__:
            from apps.debug import swipe_signal

            swipe = await loop.race(Swipe(directions), swipe_signal())
        else:
            swipe = await Swipe(directions)

        if swipe is SWIPE_UP:
            self.page = min(self.page + 1, len(self.pages) - 1)
        elif swipe is SWIPE_DOWN:
            self.page = max(self.page - 1, 0)

        self.pages[self.page].dispatch(ui.REPAINT, 0, 0)
        self.repaint = True

        if __debug__:
            from apps.debug import notify_layout_change

            notify_layout_change(self)

        self.on_change()

    def create_tasks(self) -> tuple[loop.Task, ...]:
        tasks: tuple[loop.Task, ...] = (
            self.handle_input(),
            self.handle_rendering(),
            self.handle_paging(),
        )

        if __debug__:
            # XXX This isn't strictly correct, as it allows *any* Paginated layout to be
            # shut down by a DebugLink confirm, even if used outside of a confirm() call
            # But we don't have any such usages in the codebase, and it doesn't actually
            # make much sense to use a Paginated without a way to confirm it.
            from apps.debug import confirm_signal

            return tasks + (confirm_signal(),)
        else:
            return tasks

    def on_change(self) -> None:
        if self.one_by_one:
            raise ui.Result(self.page)

    if __debug__:

        def read_content(self) -> list[str]:
            return self.pages[self.page].read_content()


class PageWithButtons(ui.Component):
    def __init__(
        self,
        content: ui.Component,
        paginated: "PaginatedWithButtons",
        index: int,
        count: int,
    ) -> None:
        super().__init__()
        self.content = content
        self.paginated = paginated
        self.index = index
        self.count = count

        # somewhere in the middle, we can go up or down
        left = res.load(ui.ICON_BACK)
        left_style = ButtonDefault
        right = res.load(ui.ICON_CLICK)
        right_style = ButtonDefault

        if self.index == 0:
            # first page, we can cancel or go down
            left = res.load(ui.ICON_CANCEL)
            left_style = ButtonCancel
            right = res.load(ui.ICON_CLICK)
            right_style = ButtonDefault
        elif self.index == count - 1:
            # last page, we can go up or confirm
            left = res.load(ui.ICON_BACK)
            left_style = ButtonDefault
            right = res.load(ui.ICON_CONFIRM)
            right_style = ButtonConfirm

        self.left = Button(ui.grid(8, n_x=2), left, left_style)
        self.left.on_click = self.on_left  # type: ignore

        self.right = Button(ui.grid(9, n_x=2), right, right_style)
        self.right.on_click = self.on_right  # type: ignore

    def dispatch(self, event: int, x: int, y: int) -> None:
        self.content.dispatch(event, x, y)
        self.left.dispatch(event, x, y)
        self.right.dispatch(event, x, y)

    def on_left(self) -> None:
        if self.index == 0:
            self.paginated.on_cancel()
        else:
            self.paginated.on_up()

    def on_right(self) -> None:
        if self.index == self.count - 1:
            self.paginated.on_confirm()
        else:
            self.paginated.on_down()

    if __debug__:

        def read_content(self) -> list[str]:
            return self.content.read_content()


class PaginatedWithButtons(ui.Layout):
    def __init__(
        self, pages: list[ui.Component], page: int = 0, one_by_one: bool = False
    ) -> None:
        super().__init__()
        self.pages = [
            PageWithButtons(p, self, i, len(pages)) for i, p in enumerate(pages)
        ]
        self.page = page
        self.one_by_one = one_by_one

    def dispatch(self, event: int, x: int, y: int) -> None:
        pages = self.pages
        page = self.page
        pages[page].dispatch(event, x, y)
        if event is ui.RENDER:
            render_scrollbar(len(pages), page)

    def on_up(self) -> None:
        self.page = max(self.page - 1, 0)
        self.pages[self.page].dispatch(ui.REPAINT, 0, 0)
        self.on_change()

    def on_down(self) -> None:
        self.page = min(self.page + 1, len(self.pages) - 1)
        self.pages[self.page].dispatch(ui.REPAINT, 0, 0)
        self.on_change()

    def on_confirm(self) -> None:
        raise ui.Result(CONFIRMED)

    def on_cancel(self) -> None:
        raise ui.Result(CANCELLED)

    def on_change(self) -> None:
        if self.one_by_one:
            raise ui.Result(self.page)

    if __debug__:

        def read_content(self) -> list[str]:
            return self.pages[self.page].read_content()

        def create_tasks(self) -> tuple[loop.Task, ...]:
            from apps.debug import confirm_signal

            return super().create_tasks() + (confirm_signal(),)


def paginate_text(
    text: str,
    header: str,
    font: int = ui.NORMAL,
    header_icon: str = ui.ICON_DEFAULT,
    icon_color: int = ui.ORANGE_ICON,
    break_words: bool = False,
) -> Confirm | Paginated:
    span = Span(text, 0, font, break_words=break_words)
    if span.count_lines() <= TEXT_MAX_LINES:
        result = Text(
            header,
            header_icon=header_icon,
            icon_color=icon_color,
            new_lines=False,
            break_words=break_words,
        )
        result.content = [font, text]
        return Confirm(result)

    else:
        pages: list[ui.Component] = []
        span.reset(
            text, 0, font, break_words=break_words, line_width=_PAGINATED_LINE_WIDTH
        )
        while span.has_more_content():
            # advance to first line of the page
            span.next_line()
            page = Text(
                header,
                header_icon=header_icon,
                icon_color=icon_color,
                new_lines=False,
                content_offset=0,
                char_offset=span.start,
                line_width=_PAGINATED_LINE_WIDTH,
                break_words=break_words,
                render_page_overflow=False,
            )
            page.content = [font, text]
            pages.append(page)

            # roll over the remaining lines on the page
            for _ in range(TEXT_MAX_LINES - 1):
                span.next_line()

        pages[-1] = Confirm(pages[-1])
        return Paginated(pages)
