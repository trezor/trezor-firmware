"""The contact name of an external output (pay-to-contact).

The recipient's Trezor attested the output address with its contact identity
key (apps.common.contacts). This Trezor names the output only if that
attestation verifies and the user's own WARD holds a plain-text name for the
identity that a WM-attested head in this session proves current. Anything
else, including every failure to get or check the WARD proof, leaves the bare
address on the screen, as without contact data.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import TxOutput

    from apps.common.coininfo import CoinInfo

# The caller's identity for apps.ward.label, never taken from the wire.
_PRINCIPAL = "sign_tx"


async def contact_label(txo: TxOutput, coin: CoinInfo) -> str | None:
    """The contact name to show for `txo`, or None. The field shapes were checked
    when the output was received (helpers._sanitize_tx_output)."""
    from trezor import utils

    pubkey = txo.contact_pubkey
    signature = txo.contact_signature
    address = txo.address
    if utils.BITCOIN_ONLY or pubkey is None or signature is None or address is None:
        return None

    from apps.common import contacts

    # Verified before any pull, so the host cannot make the device read an entry
    # for an identity that did not sign this address.
    if not contacts.verify_attestation(pubkey, signature, coin.slip44, address):
        return None

    from trezor import log
    from trezor.wire import ActionCancelled
    from trezor.wire.context import UnexpectedMessageException
    from trezor.wire.protocol_common import ChannelPreemptedException, WireError

    from apps.ward import label, offline_store
    from apps.ward.keys import ENTRY_TYPE_ADDRESS

    identifier = contacts.encode_npub(pubkey).encode()
    try:
        # A queued change that is not published yet may be about to replace or
        # remove the published name.
        status, entry = await offline_store.get(
            ENTRY_TYPE_ADDRESS, contacts.WARD_DOMAIN, identifier
        )
        if status == offline_store.CORRUPT or (entry is not None and entry.pending):
            return None
        value, note = await label.resolve_label(
            _PRINCIPAL, identifier, domain=contacts.WARD_DOMAIN
        )
    except (
        UnexpectedMessageException,
        ActionCancelled,
        WireError,
        ChannelPreemptedException,
    ):
        # The host answered the pull with another message, or the session is gone:
        # signing ends, as it would at any other step.
        raise
    except Exception as e:
        # As in apps.display_address.show: failing to name a payee is not a
        # payment failure.
        log.warning(__name__, "contact lookup failed (%s): %s", type(e).__name__, e)
        return None

    # Offline, pending and proven-only copies are not shown: a name on the screen
    # must mean it was checked against the head the WM attested.
    if value is None or note != label.NOTE_CURRENT:
        return None
    return contacts.display_name(value)
