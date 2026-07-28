from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import DisplayAddressWithProof, Success


async def show_with_proof(msg: "DisplayAddressWithProof") -> "Success":
    """PUSH: the host attaches the WARD proof up-front. The firmware verifies the
    supplied (membership: value/counter; non-membership: witness_*) proof against
    its authenticated WARD root and shows the verified label. The PULL variant is
    apps.display_address.show.
    """
    from trezor.messages import Success
    from trezor.ui.layouts import show_address

    from apps.common import ward as ward_core

    status, label = await ward_core.verify_label(
        "display_address",
        msg.address.encode(),
        msg.value,
        msg.proof,
        msg.counter,
        witness_address=msg.witness_address,
        witness_value=msg.witness_value,
        witness_counter=msg.witness_counter,
    )

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
