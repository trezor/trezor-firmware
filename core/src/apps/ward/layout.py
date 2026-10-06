from . import WardApp

_APP_LABELS = {
    WardApp.BITCOIN: "Bitcoin",
}


async def confirm_store(app: int, key: str, value: str, old_value: str | None) -> None:
    """Ask the user to approve storing `value` under `key`.

    `old_value` is the value being replaced, if any.
    """
    from trezor.enums import ButtonRequestType
    from trezor.ui.layouts import confirm_properties

    if old_value is None:
        await confirm_properties(
            "ward_store",
            "Store data",
            (("Key", key, None), ("Value", value, None)),
            subtitle=_APP_LABELS[app],
            br_code=ButtonRequestType.Other,
        )
    else:
        await confirm_properties(
            "ward_replace",
            "Replace data",
            (
                ("Key", key, None),
                ("Current value", old_value, None),
                ("New value", value, None),
            ),
            subtitle=_APP_LABELS[app],
            hold=True,
            br_code=ButtonRequestType.Other,
        )


async def confirm_delete(app: int, key: str, value: str) -> None:
    """Ask the user to approve deleting `value` stored under `key`."""
    from trezor.enums import ButtonRequestType
    from trezor.ui.layouts import confirm_properties

    await confirm_properties(
        "ward_delete",
        "Delete data",
        (("Key", key, None), ("Value", value, None)),
        subtitle=_APP_LABELS[app],
        hold=True,
        br_code=ButtonRequestType.Other,
    )
