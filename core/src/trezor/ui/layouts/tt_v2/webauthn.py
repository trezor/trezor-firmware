from typing import TYPE_CHECKING

from trezor.enums import ButtonRequestType

import trezorui2

from ...components.common.confirm import is_confirmed
from ...components.common.webauthn import ConfirmInfo
from ..common import interact
from . import _RustLayout

if TYPE_CHECKING:
    from trezor.wire import GenericContext

    Pageable = object


async def confirm_webauthn(
    ctx: GenericContext | None,
    info: ConfirmInfo,
    pageable: Pageable | None = None,
) -> bool:
    if pageable is not None:
        raise NotImplementedError

    confirm = _RustLayout(
        trezorui2.confirm_blob(
            title=info.get_header().upper(),
            data=f"{info.app_name()}\n{info.account_name()}",
        )
    )

    if ctx is None:
        return is_confirmed(await confirm)
    else:
        return is_confirmed(
            await interact(ctx, confirm, "confirm_webauthn", ButtonRequestType.Other)
        )


async def confirm_webauthn_reset() -> bool:
    return is_confirmed(
        await _RustLayout(
            trezorui2.confirm_blob(
                title="FIDO2 RESET",
                data="Do you really want to\nerase all credentials?",
            )
        )
    )
