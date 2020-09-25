from trezor import ui, utils

if False:
    from typing import Callable, Dict, List, Union

if utils.MODEL == "1":
    from .t1 import layout
elif utils.MODEL == "T":
    from .tt import layout  # type: ignore
else:
    raise ValueError("Unknown Trezor model")


def lookup_layout(brtype: str, content: Dict[str, Union[str, List[str]]]) -> ui.Layout:
    l = getattr(layout, brtype)  # type: Callable[..., ui.Layout]

    # FIXME perhaps move this to interact()?
    # also convert all scalars to string before passing them to button_request or the layout function
    # maybe add third category of security-sensitive items not to be sent over wire
    lists = {k: v for (k, v) in content.items() if isinstance(v, list)}
    strings = {k: v for (k, v) in content.items() if not isinstance(v, list)}
    if len(lists) == 0:
        return l(**strings)
    else:
        return l(**strings, _lists=lists)
