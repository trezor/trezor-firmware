from trezor.crypto import hashlib

knownapps = {
    hashlib.sha256(
        b"https://account.gandi.net/api/u2f/trusted_facets.json"
    ).digest(): "Gandi",
    hashlib.sha256(b"https://api-9dcf9b83.duosecurity.com").digest(): "Duo",
    hashlib.sha256(b"https://bitbucket.org").digest(): "Bitbucket",
    hashlib.sha256(b"https://dashboard.stripe.com").digest(): "Stripe",
    hashlib.sha256(b"https://demo.yubico.com").digest(): "Yubico U2F Demo",
    hashlib.sha256(b"https://github.com/u2f/trusted_facets").digest(): "GitHub",
    hashlib.sha256(b"https://gitlab.com").digest(): "GitLab",
    hashlib.sha256(b"https://keepersecurity.com").digest(): "Keeper",
    hashlib.sha256(
        b"https://slushpool.com/static/security/u2f.json"
    ).digest(): "Slush Pool",
    hashlib.sha256(b"https://u2f.bin.coffee").digest(): "u2f.bin.coffee checker",
    hashlib.sha256(b"https://vault.bitwarden.com/app-id.json").digest(): "bitwarden",
    hashlib.sha256(b"https://www.bitfinex.com").digest(): "Bitfinex",
    hashlib.sha256(b"https://www.dropbox.com/u2f-app-id.json").digest(): "Dropbox",
    hashlib.sha256(b"https://www.fastmail.com").digest(): "FastMail",
    hashlib.sha256(
        b"https://www.gstatic.com/securitykey/origins.json"
    ).digest(): "Google",
}
