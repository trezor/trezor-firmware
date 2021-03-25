from trezor import ui, wire
from trezor.enums import ButtonRequestType

from ...components.common.confirm import is_confirmed
from ...components.common.webauthn import ConfirmInfo
from ...components.tt.confirm import Confirm, ConfirmPageable, Pageable
from ...components.tt.text import Text
from ...components.tt.webauthn import ConfirmContent
from ..common import interact

if False:
    from typing import Optional


async def confirm_webauthn(
    ctx: Optional[wire.GenericContext],
    info: ConfirmInfo,
    pageable: Optional[Pageable] = None,
) -> bool:
    if pageable is not None:
        confirm: ui.Layout = ConfirmPageable(pageable, ConfirmContent(info))
    else:
        confirm = Confirm(ConfirmContent(info))

    if ctx is None:
        return is_confirmed(await confirm)
    else:
        return is_confirmed(
            await interact(ctx, confirm, "confirm_webauthn", ButtonRequestType.Other)
        )


async def confirm_webauthn_reset() -> bool:
    text = Text("FIDO2 Reset", ui.ICON_CONFIG)
    text.normal("Do you really want to")
    text.bold("erase all credentials?")
    return is_confirmed(await Confirm(text))
