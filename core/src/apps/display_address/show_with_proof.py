from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import DisplayAddressWithProof, Success


async def show_with_proof(msg: "DisplayAddressWithProof") -> "Success":
    """PUSH: the host attaches the WARD proof up-front. The firmware verifies the
    supplied (membership: the leaf's two parts; non-membership: witness hashes) proof
    against its authenticated WARD root and shows the verified label. The PULL
    variant is apps.display_address.show.
    """
    from trezor import utils
    from trezor.messages import Success
    from trezor.ui.layouts import show_address, show_warning
    from trezor.wire import DataError

    from apps.common import ward as ward_core
    from apps.ward import service

    m_val = ward_core.read_leaf_content(msg.content)
    m_key_type, m_id = ward_core.read_leaf_identity(msg.identity)
    label_text: str | None = None
    try:
        from apps.ward.caller import DISPLAY_ADDRESS, host_caller

        # Domain and key type are the WARD service's; a host naming others is refused.
        host_caller(msg.app_id, m_key_type, None)
        status, label = await ward_core.verify_label(
            DISPLAY_ADDRESS,
            msg.address.encode(),
            m_id,
            m_val,
            [bytes(node) for node in msg.proof],
            witness_entry_key=(
                bytes(msg.witness_entry_key)
                if msg.witness_entry_key is not None
                else None
            ),
            witness_commit=(
                bytes(msg.witness_commit) if msg.witness_commit is not None else None
            ),
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
            label_text = (
                service.display_text(bytes(label)) if label is not None else None
            )
            if label is not None and label_text is None:
                # The subtitle carries no field name to mark a hex form, so a label that is
                # not plain text is not shown at all rather than shown ambiguously.
                await show_warning(
                    "display_address/ward_label_not_text",
                    "WARD label not shown",
                    "The verified label is not plain text.",
                )
        elif status == "unknown":
            await show_warning(
                "display_address/ward_error",
                "WARD label could not be verified",
                "The proof did not match the device's authenticated root.",
            )

    # Bolt and Caesar show no subtitle: there the label goes above the address.
    label_above = utils.UI_LAYOUT in ("BOLT", "CAESAR")
    await show_address(
        msg.address,
        title=status,
        subtitle=None if label_above else label_text,
        network=label_text if label_above else None,
        case_sensitive=bool(msg.case_sensitive),
        chunkify=bool(msg.chunkify),
        br_name="display_address/show",
    )

    return Success(message="Address shown")
