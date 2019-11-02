from micropython import const

from trezor import ui
from trezor.messages import ButtonRequestType
from trezor.ui.text import Text

from apps.common import HARDENED
from apps.common.confirm import require_confirm

if False:
    from typing import Any, Callable, List
    from trezor import wire
    from apps.common import seed


async def validate_path(
    ctx: wire.Context,
    validate_func: Callable[..., bool],
    keychain: seed.Keychain,
    path: List[int],
    curve: str,
    **kwargs: Any,
) -> None:
    print("----COMMON VALIDATE PATHS----", path, curve)
    keychain.validate_path(path, curve)
    print("----COMMON VALIDATE PATH keychain.validate_path() success----", keychain, curve)
    if not validate_func(path, **kwargs):
        await show_path_warning(ctx, path)


async def show_path_warning(ctx: wire.Context, path: List[int]) -> None:
    text = Text("Confirm path", ui.ICON_WRONG, ui.RED)
    text.normal("Path")
    text.mono(*break_address_n_to_lines(path))
    text.normal("is unknown.")
    text.normal("Are you sure?")
    await require_confirm(ctx, text, ButtonRequestType.UnknownDerivationPath)


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
    else:
        return False


def break_address_n_to_lines(address_n: list) -> list:
    def path_item(i: int) -> str:
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
