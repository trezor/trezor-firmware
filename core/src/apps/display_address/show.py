from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import DisplayAddress, Success


async def show(msg: "DisplayAddress") -> "Success":
    from trezor.messages import Success
    from trezor.ui.layouts import show_address

    from apps.common import ward as ward_core

    address = msg.address.encode()

    # PUSH: the host attached a proof to this message; verify it directly.
    # PULL: no pushed proof — request one from the host on demand. Either path
    # verifies against the device's authenticated WARD root and returns the same
    # (status, label). An empty proof list is valid for single-leaf membership,
    # so detect PUSH via the presence of ward_value/ward_counter, not the proof.
    if msg.ward_value is not None and msg.ward_counter is not None:
        status, label = await ward_core.verify_label(
            "display_address",
            address,
            msg.ward_value,
            msg.ward_proof,
            msg.ward_counter,
        )
    else:
        status, label = await ward_core.resolve_label("display_address", address)

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
