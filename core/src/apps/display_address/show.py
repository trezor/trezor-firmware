from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import DisplayAddress, Success


async def show(msg: "DisplayAddress") -> "Success":
    """PULL: the device requests the WARD proof on demand (WARDProofRequest), the
    host answers (WARDProofAck), and the label is verified against the device's
    authenticated WARD root. The PUSH variant is apps.display_address.show_with_proof.
    """
    from trezor.messages import Success
    from trezor.ui.layouts import show_address

    from apps.common import ward as ward_core

    status, label = await ward_core.resolve_label("display_address", msg.address.encode())

    label_text = bytes(label).decode() if label is not None else None

    await show_address(
        msg.address,
        title=status,
        subtitle=label_text,
        case_sensitive=bool(msg.case_sensitive),
        chunkify=bool(msg.chunkify),
        br_name="display_address/show",
    )

    return Success(message="Address shown")
