from typing import TYPE_CHECKING

from trezor import wire

from ...components.common.webauthn import ConfirmInfo

if TYPE_CHECKING:
    Pageable = object


async def confirm_webauthn(
    ctx: wire.GenericContext | None,
    info: ConfirmInfo,
    pageable: Pageable | None = None,
) -> bool:
    raise NotImplementedError


async def confirm_webauthn_reset() -> bool:
    raise NotImplementedError
