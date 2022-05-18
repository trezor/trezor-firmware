from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...components.common.webauthn import ConfirmInfo
    from trezor import wire

    Pageable = object


async def confirm_webauthn(
    ctx: wire.GenericContext | None,
    info: ConfirmInfo,
    pageable: Pageable | None = None,
) -> bool:
    raise NotImplementedError


async def confirm_webauthn_reset() -> bool:
    raise NotImplementedError
