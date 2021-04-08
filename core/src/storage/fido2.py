# FIDO2 keys that should be generated once per power-up
# https://fidoalliance.org/specs/fido-v2.0-ps-20190130/fido-client-to-authenticator-protocol-v2.0-ps-20190130.html#authenticator-power-up-configuration
# While we could safely generate these keys per-wipe and save them in sessionless cache,
# this drags down the performance of our test suite.

# We want to avoid importing `trezor.crypto.curve` because that would needlessly pollute
# our RAM space, while in the end importing the symbol from `trezorcrypto` directly anyway
from trezorcrypto import nist256p1

# the authenticatorKeyAgreementKey used for ECDH in authenticatorClientPIN getKeyAgreement.
KEY_AGREEMENT_PRIVKEY = nist256p1.generate_secret()
KEY_AGREEMENT_PUBKEY = nist256p1.publickey(KEY_AGREEMENT_PRIVKEY, False)
