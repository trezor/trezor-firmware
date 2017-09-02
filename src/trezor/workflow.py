from trezor import log
from trezor import loop
from trezor import ui

started = []
default = None
default_handler = None


def onstart(w):
    closedefault()
    started.append(w)
    ui.display.backlight(ui.BACKLIGHT_NORMAL)
    log.debug(__name__, 'onstart: %s', w)


def onclose(w):
    started.remove(w)
    log.debug(__name__, 'onclose: %s', w)

    if not started and default_handler:
        startdefault(default_handler)


def closedefault():
    global default

    if default:
        default.close()
        default = None
        log.debug(__name__, 'closedefault')


def startdefault(handler):
    global default
    global default_handler

    if not default:
        default_handler = handler
        default = handler()
        loop.schedule_task(default)
        ui.display.backlight(ui.BACKLIGHT_NORMAL)
        log.debug(__name__, 'startdefault')
