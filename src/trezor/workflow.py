from trezor import log, loop, ui

_started = []
_default = None
_default_genfunc = None


def start_default(genfunc):
    global _default
    global _default_genfunc
    _default_genfunc = genfunc
    _default = _default_genfunc()
    log.info(__name__, 'start default %s', _default)
    loop.schedule_task(_default)
    ui.display.backlight(ui.BACKLIGHT_NORMAL)


def close_default():
    global _default
    log.info(__name__, 'close default %s', _default)
    _default.close()
    _default = None


def start(workflow):
    if _default is not None:
        close_default()
    _started.append(workflow)
    log.info(__name__, 'start %s', workflow)
    loop.schedule_task(_watch(workflow))
    ui.display.backlight(ui.BACKLIGHT_NORMAL)


async def _watch(workflow):
    try:
        return await workflow
    finally:
        _started.remove(workflow)
        if not _started and _default_genfunc is not None:
            start_default(_default_genfunc)
