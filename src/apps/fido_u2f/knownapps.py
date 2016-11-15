from trezor.crypto import hashlib

knownapps = {
    hashlib.sha256(b'https://bitbucket.org').digest()                            : 'Bitbucket',
    hashlib.sha256(b'https://www.dropbox.com/u2f-app-id.json').digest()          : 'Dropbox',
    hashlib.sha256(b'https://www.fastmail.com').digest()                         : 'FastMail',
    hashlib.sha256(b'https://github.com/u2f/trusted_facets').digest()            : 'GitHub',
    hashlib.sha256(b'https://gitlab.com').digest()                               : 'GitLab',
    hashlib.sha256(b'https://www.gstatic.com/securitykey/origins.json').digest() : 'Google',
    hashlib.sha256(b'https://slushpool.com/static/security/u2f.json').digest()   : 'Slush Pool',
    hashlib.sha256(b'https://demo.yubico.com').digest()                          : 'Yubico U2F Demo',
}
