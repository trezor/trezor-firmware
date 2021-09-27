from trezor import ui

from .button import Button
from .num_input import NumInput
from .text import Text

if False:
    from trezor import loop
    from typing import Callable, NoReturn, Sequence

if __debug__:
    from apps import debug


class Slip39NumInput(ui.Component):
    SET_SHARES = object()
    SET_THRESHOLD = object()
    SET_GROUPS = object()
    SET_GROUP_THRESHOLD = object()

    def __init__(
        self,
        step: object,
        count: int,
        min_count: int,
        max_count: int,
        group_id: int | None = None,
    ) -> None:
        super().__init__()
        self.step = step
        self.input = NumInput(count, min_count=min_count, max_count=max_count)
        self.input.on_change = self.on_change  # type: ignore
        self.group_id = group_id

    def dispatch(self, event: int, x: int, y: int) -> None:
        self.input.dispatch(event, x, y)
        if event is ui.RENDER:
            self.on_render()

    def on_render(self) -> None:
        if self.repaint:
            count = self.input.count

            # render the headline
            if self.step is Slip39NumInput.SET_SHARES:
                header = "Set num. of shares"
            elif self.step is Slip39NumInput.SET_THRESHOLD:
                header = "Set threshold"
            elif self.step is Slip39NumInput.SET_GROUPS:
                header = "Set num. of groups"
            elif self.step is Slip39NumInput.SET_GROUP_THRESHOLD:
                header = "Set group threshold"
            ui.header(header, ui.ICON_RESET, ui.TITLE_GREY, ui.BG, ui.ORANGE_ICON)

            # render the counter
            if self.step is Slip39NumInput.SET_SHARES:
                if self.group_id is None:
                    if count == 1:
                        first_line_text = "Only one share will"
                        second_line_text = "be created."
                    else:
                        first_line_text = f"{count} people or locations"
                        second_line_text = "will each hold one share."
                else:
                    first_line_text = "Set the total number of"
                    second_line_text = f"shares in Group {self.group_id + 1}."
                ui.display.bar(0, 110, ui.WIDTH, 52, ui.BG)
                ui.display.text(12, 130, first_line_text, ui.NORMAL, ui.FG, ui.BG)
                ui.display.text(12, 156, second_line_text, ui.NORMAL, ui.FG, ui.BG)
            elif self.step is Slip39NumInput.SET_THRESHOLD:
                if self.group_id is None:
                    first_line_text = "For recovery you need"
                    if count == 1:
                        second_line_text = "1 share."
                    elif count == self.input.max_count:
                        second_line_text = f"all {count} of the shares."
                    else:
                        second_line_text = f"any {count} of the shares."
                else:
                    first_line_text = "The required number of "
                    second_line_text = f"shares to form Group {self.group_id + 1}."
                ui.display.bar(0, 110, ui.WIDTH, 52, ui.BG)
                ui.display.text(12, 130, first_line_text, ui.NORMAL, ui.FG, ui.BG)
                ui.display.text(12, 156, second_line_text, ui.NORMAL, ui.FG, ui.BG)
            elif self.step is Slip39NumInput.SET_GROUPS:
                ui.display.bar(0, 110, ui.WIDTH, 52, ui.BG)
                ui.display.text(
                    12, 130, "A group is made up of", ui.NORMAL, ui.FG, ui.BG
                )
                ui.display.text(12, 156, "recovery shares.", ui.NORMAL, ui.FG, ui.BG)
            elif self.step is Slip39NumInput.SET_GROUP_THRESHOLD:
                ui.display.bar(0, 110, ui.WIDTH, 52, ui.BG)
                ui.display.text(
                    12, 130, "The required number of", ui.NORMAL, ui.FG, ui.BG
                )
                ui.display.text(
                    12, 156, "groups for recovery.", ui.NORMAL, ui.FG, ui.BG
                )

            self.repaint = False

    def on_change(self, count: int) -> None:
        self.repaint = True


class MnemonicWordSelect(ui.Layout):
    NUM_OF_CHOICES = 3

    def __init__(
        self,
        words: Sequence[str],
        share_index: int | None,
        word_index: int,
        count: int,
        group_index: int | None = None,
    ) -> None:
        super().__init__()
        self.words = words
        self.share_index = share_index
        self.word_index = word_index
        self.buttons = []
        for i, word in enumerate(words):
            area = ui.grid(i + 2, n_x=1)
            btn = Button(area, word)
            btn.on_click = self.select(word)  # type: ignore
            self.buttons.append(btn)
        if share_index is None:
            self.text: ui.Component = Text("Check seed")
        elif group_index is None:
            self.text = Text(f"Check share #{share_index + 1}")
        else:
            self.text = Text(f"Check G{group_index + 1} - Share {share_index + 1}")
        self.text.normal(f"Select word {word_index + 1} of {count}:")

    def dispatch(self, event: int, x: int, y: int) -> None:
        for btn in self.buttons:
            btn.dispatch(event, x, y)
        self.text.dispatch(event, x, y)

    def select(self, word: str) -> Callable:
        def fn() -> NoReturn:
            raise ui.Result(word)

        return fn

    if __debug__:

        def read_content(self) -> list[str]:
            return self.text.read_content() + [b.text for b in self.buttons]

        def create_tasks(self) -> tuple[loop.Task, ...]:
            return super().create_tasks() + (debug.input_signal(),)
