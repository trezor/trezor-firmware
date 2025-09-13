from trezor import io
from trezorui_api import BacklightLevels, backlight_fade, backlight_get, backlight_set

_AUTODIM_FROM: int | None = None
"""Indicates whether the display is auto-dimmed. If so, it stores the user-set backlight level."""


def autodim_display() -> None:
    """Autodim the display if the device is not connected to USB."""
    global _AUTODIM_FROM
    if io.pm.is_usb_connected():
        return
    current_backlight = backlight_get()
    if current_backlight > BacklightLevels.LOW:
        _AUTODIM_FROM = current_backlight
        backlight_fade(BacklightLevels.LOW)


def autodim_clear() -> None:
    """Clear autodim state and restore previous backlight level if applicable."""
    global _AUTODIM_FROM
    if _AUTODIM_FROM is not None:
        backlight_set(_AUTODIM_FROM)
        _AUTODIM_FROM = None
