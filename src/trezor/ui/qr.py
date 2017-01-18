from trezor import ui


class Qr:

    def __init__(self, data, pos, scale):
        self.data = data
        self.pos = pos
        self.scale = scale

    def render(self):
        ui.display.qrcode(self.pos[0], self.pos[1], self.data, self.scale)

    def send(self, event, pos):
        pass
