from trezor.crypto.hashlib import sha256

# contents generated via script in
# trezor-common/defs/webauthn/gen.py
# do not edit manually

_knownapps = {
    # U2F
    "https://bitbucket.org": "Bitbucket",
    "https://www.bitfinex.com": "Bitfinex",
    "https://vault.bitwarden.com/app-id.json": "Bitwarden",
    "https://www.dashlane.com": "Dashlane",
    "https://www.dropbox.com/u2f-app-id.json": "Dropbox",
    "https://api-9dcf9b83.duosecurity.com": "Duo",
    "https://www.fastmail.com": "FastMail",
    "https://id.fedoraproject.org/u2f-origins.json": "Fedora",
    "https://account.gandi.net/api/u2f/trusted_facets.json": "Gandi",
    "https://github.com/u2f/trusted_facets": "GitHub",
    "https://gitlab.com": "GitLab",
    "https://www.gstatic.com/securitykey/origins.json": "Google",
    "https://keepersecurity.com": "Keeper",
    "https://lastpass.com": "LastPass",
    "https://slushpool.com/static/security/u2f.json": "Slush Pool",
    "https://dashboard.stripe.com": "Stripe",
    "https://u2f.bin.coffee": "u2f.bin.coffee",
    # WebAuthn
    "www.binance.com": "Binance",
    "www.dropbox.com": "Dropbox",
    "secure.login.gov": "login.gov",
    "login.microsoft.com": "Microsoft",
    "webauthn.bin.coffee": "webauthn.bin.coffee",
    "webauthn.io": "WebAuthn.io",
    "webauthn.me": "WebAuthn.me",
    "demo.yubico.com": "demo.yubico.com",
}

knownapps = {sha256(k).digest(): v for (k, v) in _knownapps.items()}
