import utime

from . import log
from . import utils


class ChangeLayoutException(Exception):

    def __init__(self, layout):
        self.layout = layout


def change(layout):
    raise ChangeLayoutException(layout)


def set_main(main_layout):
    layout = main_layout()

    while True:
        try:
            layout = yield from layout
        except ChangeLayoutException as e:
            layout = e.layout
        except Exception as e:
            log.exception(__name__, e)
            utime.sleep(1)  # Don't produce wall of exceptions

        if not isinstance(layout, utils.type_gen):
            log.info(__name__, 'Switching to main layout %s', main_layout)
            layout = main_layout()
        else:
            log.info(__name__, 'Switching to proposed layout %s', layout)
