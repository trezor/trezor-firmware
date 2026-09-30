from . import WardApp

_APP_LABELS = {
    WardApp.BITCOIN: "Bitcoin",
}


async def confirm_replace(app: int, description: str) -> None:
    """Ask the user to approve replacing the record described by `description`."""
    from trezor import TR
    from trezor.ui.layouts import confirm_action

    await confirm_action(
        "ward_replace",
        "Replace data",
        description,
        f"Stored by the {_APP_LABELS[app]} app. The current version will be lost.",
        verb=TR.buttons__hold_to_confirm,
        hold=True,
        hold_danger=True,
    )


async def confirm_delete(app: int, description: str) -> None:
    """Ask the user to approve deleting the record described by `description`."""
    from trezor import TR
    from trezor.ui.layouts import confirm_action

    await confirm_action(
        "ward_delete",
        "Delete data",
        description,
        f"Stored by the {_APP_LABELS[app]} app. This cannot be undone.",
        verb=TR.buttons__hold_to_confirm,
        hold=True,
        hold_danger=True,
    )
