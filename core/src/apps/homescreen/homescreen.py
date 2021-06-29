from apps.base import lock_device


async def homescreen() -> None:
    from trezor.ui.layouts import homescreen as homescreen_layout

    await homescreen_layout()
    lock_device()
