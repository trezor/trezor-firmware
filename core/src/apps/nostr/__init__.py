if not __debug__:
    from trezor import utils

    utils.halt("Disabled in production mode")

from apps.common.paths import PATTERN_BIP44

CURVE = "secp256k1"
SLIP44_ID = 1237

# Note: we are not satisfied with using this path even though it is defined in NIP-06.
# See this issue for details: https://github.com/nostr-protocol/nips/issues/1774
# TODO: we need to create a new NIP using a different derivation path and use that here!
PATTERN = PATTERN_BIP44
