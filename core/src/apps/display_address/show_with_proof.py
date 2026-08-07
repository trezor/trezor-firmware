from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import DisplayAddressWithProof, Success


async def show_with_proof(msg: "DisplayAddressWithProof") -> "Success":
    """PUSH: the host attaches the WARD proof up-front. The firmware verifies the
    supplied (membership: value/counter; non-membership: witness hashes) proof
    against its authenticated WARD root and shows the verified label. The PULL
    variant is apps.display_address.show.
    """
    from trezor.messages import Success
    from trezor.ui.layouts import show_address, show_warning
    from trezor.wire import DataError

    from apps.common import ward as ward_core

    m_nonce, m_tag, m_ct = ward_core.read_leaf_content(msg.content)
    label_text: str | None = None
    try:
        status, label = await ward_core.verify_label(
            "display_address",
            msg.address.encode(),
            m_nonce,
            m_tag,
            m_ct,
            msg.proof,
            entry_type=msg.entry_type or "address",
            witness_entry_key=msg.witness_entry_key,
            witness_commit=msg.witness_commit,
            domain=msg.app_id,
        )
    except DataError as e:
        # The pushed proof was malformed/incomplete (e.g. a non-membership claim with
        # no witness_value_hash). Show the issue ON-DEVICE rather than failing silently.
        await show_warning(
            "display_address/ward_error",
            "WARD label unavailable",
            str(e) or "The supplied label proof was incomplete.",
        )
        status = "unverified"
    else:
        if status == "membership":
            label_text = bytes(label).decode() if label is not None else None
        elif status == "unknown":
            await show_warning(
                "display_address/ward_error",
                "WARD label could not be verified",
                "The proof did not match the device's authenticated root.",
            )

    await show_address(
        msg.address,
        title=status,
        subtitle=label_text,
        case_sensitive=bool(msg.case_sensitive),
        chunkify=bool(msg.chunkify),
        br_name="display_address/show",
    )

    return Success(message="Address shown")
