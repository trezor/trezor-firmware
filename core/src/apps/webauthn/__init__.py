from trezor import loop, wire
from trezor.messages import MessageType

from .fido2 import handle_reports


def boot() -> None:
    wire.add(
        MessageType.WebAuthnListResidentCredentials,
        __name__,
        "list_resident_credentials",
    )
    wire.add(
        MessageType.WebAuthnAddResidentCredential, __name__, "add_resident_credential"
    )
    wire.add(
        MessageType.WebAuthnRemoveResidentCredential,
        __name__,
        "remove_resident_credential",
    )
    import usb

    if usb.ENABLE_IFACE_WEBAUTHN:
        loop.schedule(handle_reports(usb.iface_webauthn))
