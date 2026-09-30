from . import WardApp

_APP_LABELS = {
    WardApp.BITCOIN: "Bitcoin",
}


async def confirm_replace(app: int, description: str) -> None:
    """Ask the user to approve replacing the record described by `description`."""
    raise NotImplementedError


async def confirm_delete(app: int, description: str) -> None:
    """Ask the user to approve deleting the record described by `description`."""
    raise NotImplementedError
