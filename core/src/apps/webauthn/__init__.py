def boot() -> None:
    import usb
    from trezor import loop

    from .fido2 import handle_reports

    loop.schedule(handle_reports(usb.iface_webauthn))
