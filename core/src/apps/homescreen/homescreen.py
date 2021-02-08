import storage
import storage.device
from trezor import config, ui, loop

from . import HomescreenBase


async def homescreen() -> None:
    await Homescreen()


class Homescreen(HomescreenBase):
    def __init__(self) -> None:
        super().__init__()
        if not storage.device.is_initialized():
            self.label = "Go to trezor.io/start"

    def on_render(self) -> None:
        # warning bar on top
        if storage.device.is_initialized() and storage.device.no_backup():
            ui.header_error("SEEDLESS")
        elif storage.device.is_initialized() and storage.device.unfinished_backup():
            ui.header_error("BACKUP FAILED!")
        elif storage.device.is_initialized() and storage.device.needs_backup():
            ui.header_warning("NEEDS BACKUP!")
        elif storage.device.is_initialized() and not config.has_pin():
            ui.header_warning("PIN NOT SET!")
        elif storage.device.get_experimental_features():
            ui.header_warning("EXPERIMENTAL MODE!")
        else:
            ui.display.bar(0, 0, ui.WIDTH, ui.HEIGHT, ui.BG)

        # homescreen with shifted avatar and text on bottom
        ui.display.avatar(48, 48 - 10, self.image, ui.WHITE, ui.BLACK)
        ui.display.text_center(ui.WIDTH // 2, 220, self.label, ui.BOLD, ui.FG, ui.BG)

        def render_text(x, y, text, font, fg, bg):
            print("render", x, y, text, font, fg, bg)

        ui.display.text_rich(
            items=["abc"],
            item_offset=0,
            char_offset=0,
            # bounds
            x0=20,
            y0=20,
            x1=ui.WIDTH,
            y1=220,
            # style
            fg=0xffff,
            bg=0x0000,
            font=-1,
            break_words=True,
            insert_new_lines=True,
            render_page_overflow=True,
            render_text_fn=render_text
        )