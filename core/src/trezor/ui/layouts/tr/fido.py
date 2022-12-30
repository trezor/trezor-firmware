from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.wire import GenericContext

    Pageable = object


async def confirm_fido(
    ctx: GenericContext | None,
    header: str,
    app_name: str,
    icon_name: str | None,
    accounts: list[str | None],
) -> int:
    """Webauthn confirmation for one or more credentials."""
    raise NotImplementedError


async def confirm_fido_reset() -> bool:
    raise NotImplementedError
