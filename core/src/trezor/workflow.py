from trezor import loop

if False:
    from trezor import ui
    from typing import List, Callable, Optional

workflows = []  # type: List[loop.Task]
layouts = []  # type: List[ui.Layout]
layout_signal = loop.chan()
default = None  # type: Optional[loop.Task]
default_layout = None  # type: Optional[Callable[[], loop.Task]]


def onstart(w: loop.Task) -> None:
    workflows.append(w)


def onclose(w: loop.Task) -> None:
    workflows.remove(w)
    if not layouts and default_layout:
        startdefault(default_layout)

    if __debug__:
        import micropython
        from trezor import utils

        if utils.LOG_MEMORY:
            micropython.mem_info()


def closedefault() -> None:
    global default

    if default:
        loop.close(default)
        default = None


def startdefault(layout: Callable[[], loop.Task]) -> None:
    global default
    global default_layout

    if not default:
        default_layout = layout
        default = layout()
        loop.schedule(default)


def restartdefault() -> None:
    global default_layout

    closedefault()
    if default_layout:
        startdefault(default_layout)


def onlayoutstart(l: ui.Layout) -> None:
    closedefault()
    layouts.append(l)


def onlayoutclose(l: ui.Layout) -> None:
    if l in layouts:
        layouts.remove(l)
