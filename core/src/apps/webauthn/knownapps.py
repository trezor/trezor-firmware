from trezor.crypto.hashlib import sha256

# contents generated via script in
# trezor-common/defs/webauthn/gen.py
# do not edit manually

_knownapps = {
    # U2F
    "https://bitbucket.org": {"label": "Bitbucket", "use_sign_count": True},
    "https://www.bitfinex.com": {"label": "Bitfinex", "use_sign_count": True},
    "https://vault.bitwarden.com/app-id.json": {
        "label": "Bitwarden",
        "use_sign_count": True,
    },
    "https://www.dashlane.com": {"label": "Dashlane", "use_sign_count": True},
    "https://www.dropbox.com/u2f-app-id.json": {
        "label": "Dropbox",
        "use_sign_count": True,
    },
    "https://api-9dcf9b83.duosecurity.com": {"label": "Duo", "use_sign_count": True},
    "https://www.fastmail.com": {"label": "FastMail", "use_sign_count": True},
    "https://id.fedoraproject.org/u2f-origins.json": {
        "label": "Fedora",
        "use_sign_count": True,
    },
    "https://account.gandi.net/api/u2f/trusted_facets.json": {
        "label": "Gandi",
        "use_sign_count": True,
    },
    "https://github.com/u2f/trusted_facets": {
        "label": "GitHub",
        "use_sign_count": True,
    },
    "https://gitlab.com": {"label": "GitLab", "use_sign_count": True},
    "https://www.gstatic.com/securitykey/origins.json": {
        "label": "Google",
        "use_sign_count": True,
    },
    "https://keepersecurity.com": {"label": "Keeper", "use_sign_count": True},
    "https://lastpass.com": {"label": "LastPass", "use_sign_count": True},
    "https://slushpool.com/static/security/u2f.json": {
        "label": "Slush Pool",
        "use_sign_count": True,
    },
    "https://dashboard.stripe.com": {"label": "Stripe", "use_sign_count": True},
    "https://u2f.bin.coffee": {"label": "u2f.bin.coffee", "use_sign_count": True},
    # WebAuthn
    "www.binance.com": {"label": "Binance", "use_sign_count": False},
    "www.dropbox.com": {"label": "Dropbox"},
    "github.com": {"label": "GitHub", "use_sign_count": True},
    "google.com": {"label": "Google"},
    "secure.login.gov": {"label": "login.gov"},
    "login.microsoft.com": {"label": "Microsoft", "use_sign_count": False},
    "webauthn.bin.coffee": {"label": "webauthn.bin.coffee"},
    "webauthn.io": {"label": "WebAuthn.io"},
    "webauthn.me": {"label": "WebAuthn.me"},
    "demo.yubico.com": {"label": "demo.yubico.com"},
}

knownapps = {sha256(k.encode()).digest(): v for (k, v) in _knownapps.items()}
