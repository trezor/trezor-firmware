from trezor import ui


class Qr(ui.Control):
    def __init__(self, data, x, y, scale):
        self.data = data
        self.x = x
        self.y = y
        self.scale = scale

    def on_render(self):
        ui.display.qrcode(self.x, self.y, self.data, self.scale)
