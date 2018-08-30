from micropython import const

from trezor import ui
from trezor.messages import ButtonRequestType
from trezor.ui.text import Text

from apps.common import HARDENED
from apps.common.confirm import require_confirm


async def validate_path(ctx, validate_func, **kwargs):
    if not validate_func(**kwargs):
        await show_path_warning(ctx, kwargs["path"])


async def show_path_warning(ctx, path: list):
    text = Text("Confirm path", ui.ICON_WRONG, icon_color=ui.RED)
    text.normal("The path")
    text.mono(*break_address_n_to_lines(path))
    text.normal("seems unusual.")
    text.normal("Are you sure?")
    return await require_confirm(
        ctx, text, code=ButtonRequestType.UnknownDerivationPath
    )


def validate_path_for_get_public_key(path: list, slip44_id: int) -> bool:
    """
    Checks if path has at least three hardened items and slip44 id matches.
    The path is allowed to have more than three items, but all the following
    items have to be non-hardened.
    """
    length = len(path)
    if length < 3 or length > 5:
        return False
    if path[0] != 44 | HARDENED:
        return False
    if path[1] != slip44_id | HARDENED:
        return False
    if path[2] < HARDENED or path[2] > 20 | HARDENED:
        return False
    if length > 3 and is_hardened(path[3]):
        return False
    if length > 4 and is_hardened(path[4]):
        return False
    return True


def is_hardened(i: int) -> bool:
    if i & HARDENED:
        return True
    return False


def break_address_n_to_lines(address_n: list) -> list:
    def path_item(i: int):
        if i & HARDENED:
            return str(i ^ HARDENED) + "'"
        else:
            return str(i)

    lines = []
    path_str = "m/" + "/".join([path_item(i) for i in address_n])

    per_line = const(17)
    while len(path_str) > per_line:
        i = path_str[:per_line].rfind("/")
        lines.append(path_str[:i])
        path_str = path_str[i:]
    lines.append(path_str)

    return lines
