from trezor import ui


class Qr(ui.Component):
    def __init__(self, data: str, x: int, y: int, scale: int):
        self.data = data
        self.x = x
        self.y = y
        self.scale = scale

    def on_render(self) -> None:
        ui.display.qrcode(self.x, self.y, self.data.encode(), self.scale)
