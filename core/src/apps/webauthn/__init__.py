from trezor import io, loop, wire
from trezor.messages import MessageType

from apps.webauthn.fido2 import handle_reports


def boot(iface: io.HID) -> None:
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
    loop.schedule(handle_reports(iface))
