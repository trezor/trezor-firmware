"""The contact name of an external output (pay-to-contact).

The recipient's Trezor attested the output address with its contact identity
key (apps.common.contacts). This Trezor names the output only if that
attestation verifies and the user's own WARD holds a verified, plain-text name
for the identity. Anything else, including every failure to get or check the
WARD proof, leaves the bare address on the screen, as without contact data.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import TxOutput

    from apps.common.coininfo import CoinInfo


async def contact_label(txo: TxOutput, coin: CoinInfo) -> str | None:
    """The contact name to show for `txo`, or None. The field shapes were checked
    when the output was received (helpers._sanitize_tx_output)."""
    from trezor import utils

    pubkey = txo.contact_pubkey
    signature = txo.contact_signature
    address = txo.address
    if pubkey is None or signature is None or address is None or not utils.USE_WARD:
        return None

    from apps.common import contacts

    if not contacts.verify_attestation(pubkey, signature, coin.slip44, address):
        return None

    from trezor.wire import ActionCancelled, Error

    from apps.common import ward as ward_core
    from apps.ward import service
    from apps.ward.caller import SIGN_TX

    identifier = contacts.encode_npub(pubkey).encode()
    try:
        # A queued change (e.g. a delete) may be about to replace the committed name.
        if await _is_queued(identifier):
            return None
        status, value, freshness = await ward_core.resolve_label(SIGN_TX, identifier)
    except ActionCancelled:
        raise
    except Error:
        # No trusted root, a malformed proof, ... A host that answers the pull with
        # another message still aborts signing (UnexpectedMessageException).
        return None
    # Only a proof verified against this device's root counts: "cached" is an
    # unproven offline copy and "unverified" means the host had no proof.
    if status != "membership" or value is None:
        return None
    if freshness in (service.FRESH_BEHIND, service.FRESH_INVALID):
        return None
    return service.display_text(bytes(value))


async def _is_queued(identifier: bytes) -> bool:
    import storage.ward_store as ward_store

    from apps.ward.keys import get_wallet_id

    wallet_id = await get_wallet_id()
    for _pending_id, queued in ward_store.queue_list(wallet_id):
        if queued == identifier:
            return True
    return False
