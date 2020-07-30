# generated from knownapps.py.mako
# do not edit manually!
# flake8: noqa


if False:
    from typing import Optional


class FIDOApp:
    def __init__(
        self,
        label: str,
        icon: Optional[str],
        use_sign_count: Optional[bool],
        use_self_attestation: Optional[bool],
    ) -> None:
        self.label = label
        self.icon = icon
        self.use_sign_count = use_sign_count
        self.use_self_attestation = use_self_attestation


# fmt: off
def by_rp_id_hash(rp_id_hash: bytes) -> Optional[FIDOApp]:
    if False:
        raise RuntimeError  # if false
    elif rp_id_hash == b"\x96\x89\x78\xa2\x99\x53\xde\x52\xd3\xef\x0f\x0c\x71\xb7\xb7\xb6\xb1\xaf\x9f\x08\xe2\x57\x89\x6a\x8d\x81\x26\x91\x85\x30\x29\x3b":
        # U2F key for Amazon Web Services
        return FIDOApp(
            label="aws.amazon.com",
            icon="apps/webauthn/res/icon_aws.toif",
            use_sign_count=None,
            use_self_attestation=None,
        )
    elif rp_id_hash == b"\xc3\x40\x8c\x04\x47\x88\xae\xa5\xb3\xdf\x30\x89\x52\xfd\x8c\xa3\xc7\x0e\x21\xfe\xf4\xf6\xc1\xc2\x37\x4c\xaa\x1d\xf9\xb2\x8d\xdd":
        # WebAuthn key for Binance
        return FIDOApp(
            label="www.binance.com",
            icon="apps/webauthn/res/icon_binance.toif",
            use_sign_count=False,
            use_self_attestation=True,
        )
    elif rp_id_hash == b"\x12\x74\x3b\x92\x12\x97\xb7\x7f\x11\x35\xe4\x1f\xde\xdd\x4a\x84\x6a\xfe\x82\xe1\xf3\x69\x32\xa9\x91\x2f\x3b\x0d\x8d\xfb\x7d\x0e":
        # U2F key for Bitbucket
        return FIDOApp(
            label="bitbucket.org",
            icon="apps/webauthn/res/icon_bitbucket.toif",
            use_sign_count=None,
            use_self_attestation=None,
        )
    elif rp_id_hash == b"\x30\x2f\xd5\xb4\x49\x2a\x07\xb9\xfe\xbb\x30\xe7\x32\x69\xec\xa5\x01\x20\x5c\xcf\xe0\xc2\x0b\xf7\xb4\x72\xfa\x2d\x31\xe2\x1e\x63":
        # U2F key for Bitfinex
        return FIDOApp(
            label="www.bitfinex.com",
            icon="apps/webauthn/res/icon_bitfinex.toif",
            use_sign_count=None,
            use_self_attestation=None,
        )
    elif rp_id_hash == b"\xa3\x4d\x30\x9f\xfa\x28\xc1\x24\x14\xb8\xba\x6c\x07\xee\x1e\xfa\xe1\xa8\x5e\x8a\x04\x61\x48\x59\xa6\x7c\x04\x93\xb6\x95\x61\x90":
        # U2F key for Bitwarden
        return FIDOApp(
            label="vault.bitwarden.com",
            icon="apps/webauthn/res/icon_bitwarden.toif",
            use_sign_count=None,
            use_self_attestation=None,
        )
    elif rp_id_hash == b"\x68\x20\x19\x15\xd7\x4c\xb4\x2a\xf5\xb3\xcc\x5c\x95\xb9\x55\x3e\x3e\x3a\x83\xb4\xd2\xa9\x3b\x45\xfb\xad\xaa\x84\x69\xff\x8e\x6e":
        # U2F key for Dashlane
        return FIDOApp(
            label="www.dashlane.com",
            icon="apps/webauthn/res/icon_dashlane.toif",
            use_sign_count=None,
            use_self_attestation=None,
        )
    elif rp_id_hash == b"\xc5\x0f\x8a\x7b\x70\x8e\x92\xf8\x2e\x7a\x50\xe2\xbd\xc5\x5d\x8f\xd9\x1a\x22\xfe\x6b\x29\xc0\xcd\xf7\x80\x55\x30\x84\x2a\xf5\x81":
        # U2F key for Dropbox
        return FIDOApp(
            label="www.dropbox.com",
            icon="apps/webauthn/res/icon_dropbox.toif",
            use_sign_count=False,
            use_self_attestation=None,
        )
    elif rp_id_hash == b"\x82\xf4\xa8\xc9\x5f\xec\x94\xb2\x6b\xaf\x9e\x37\x25\x0e\x95\x63\xd9\xa3\x66\xc7\xbe\x26\x1c\xa4\xdd\x01\x01\xf4\xd5\xef\xcb\x83":
        # WebAuthn key for Dropbox
        return FIDOApp(
            label="www.dropbox.com",
            icon="apps/webauthn/res/icon_dropbox.toif",
            use_sign_count=False,
            use_self_attestation=None,
        )
    elif rp_id_hash == b"\xf3\xe2\x04\x2f\x94\x60\x7d\xa0\xa9\xc1\xf3\xb9\x5e\x0d\x2f\x2b\xb2\xe0\x69\xc5\xbb\x4f\xa7\x64\xaf\xfa\x64\x7d\x84\x7b\x7e\xd6":
        # U2F key for Duo
        return FIDOApp(
            label="duosecurity.com",
            icon="apps/webauthn/res/icon_duo.toif",
            use_sign_count=None,
            use_self_attestation=None,
        )
    elif rp_id_hash == b"\x31\x19\x33\x28\xf8\xe2\x1d\xfb\x6c\x99\xf3\x22\xd2\x2d\x7b\x0b\x50\x87\x78\xe6\x4f\xfb\xba\x86\xe5\x22\x93\x37\x90\x31\xb8\x74":
        # WebAuthn key for Facebook
        return FIDOApp(
            label="facebook.com",
            icon="apps/webauthn/res/icon_facebook.toif",
            use_sign_count=None,
            use_self_attestation=None,
        )
    elif rp_id_hash == b"\x69\x66\xab\xe3\x67\x4e\xa2\xf5\x30\x79\xeb\x71\x01\x97\x84\x8c\x9b\xe6\xf3\x63\x99\x2f\xd0\x29\xe9\x89\x84\x47\xcb\x9f\x00\x84":
        # U2F key for FastMail
        return FIDOApp(
            label="www.fastmail.com",
            icon="apps/webauthn/res/icon_fastmail.toif",
            use_sign_count=None,
            use_self_attestation=None,
        )
    elif rp_id_hash == b"\x9d\x61\x44\x2f\x5c\xe1\x33\xbd\x46\x54\x4f\xc4\x2f\x0a\x6d\x54\xc0\xde\xb8\x88\x40\xca\xc2\xb6\xae\xfa\x65\x14\xf8\x93\x49\xe9":
        # U2F key for Fedora
        return FIDOApp(
            label="fedoraproject.org",
            icon="apps/webauthn/res/icon_fedora.toif",
            use_sign_count=None,
            use_self_attestation=None,
        )
    elif rp_id_hash == b"\xa4\xe2\x2d\xca\xfe\xa7\xe9\x0e\x12\x89\x50\x11\x39\x89\xfc\x45\x97\x8d\xc9\xfb\x87\x76\x75\x60\x51\x6c\x1c\x69\xdf\xdf\xd1\x96":
        # U2F key for Gandi
        return FIDOApp(
            label="gandi.net",
            icon="apps/webauthn/res/icon_gandi.toif",
            use_sign_count=False,
            use_self_attestation=None,
        )
    elif rp_id_hash == b"\x54\xce\x65\x1e\xd7\x15\xb4\xaa\xa7\x55\xee\xce\xbd\x4e\xa0\x95\x08\x15\xb3\x34\xbd\x07\xd1\x09\x89\x3e\x96\x30\x18\xcd\xdb\xd9":
        # WebAuthn key for Gandi
        return FIDOApp(
            label="gandi.net",
            icon="apps/webauthn/res/icon_gandi.toif",
            use_sign_count=False,
            use_self_attestation=None,
        )
    elif rp_id_hash == b"\x70\x61\x7d\xfe\xd0\x65\x86\x3a\xf4\x7c\x15\x55\x6c\x91\x79\x88\x80\x82\x8c\xc4\x07\xfd\xf7\x0a\xe8\x50\x11\x56\x94\x65\xa0\x75":
        # U2F key for GitHub
        return FIDOApp(
            label="github.com",
            icon="apps/webauthn/res/icon_github.toif",
            use_sign_count=True,
            use_self_attestation=None,
        )
    elif rp_id_hash == b"\x3a\xeb\x00\x24\x60\x38\x1c\x6f\x25\x8e\x83\x95\xd3\x02\x6f\x57\x1f\x0d\x9a\x76\x48\x8d\xcd\x83\x76\x39\xb1\x3a\xed\x31\x65\x60":
        # WebAuthn key for GitHub
        return FIDOApp(
            label="github.com",
            icon="apps/webauthn/res/icon_github.toif",
            use_sign_count=True,
            use_self_attestation=None,
        )
    elif rp_id_hash == b"\xe7\xbe\x96\xa5\x1b\xd0\x19\x2a\x72\x84\x0d\x2e\x59\x09\xf7\x2b\xa8\x2a\x2f\xe9\x3f\xaa\x62\x4f\x03\x39\x6b\x30\xe4\x94\xc8\x04":
        # U2F key for GitLab
        return FIDOApp(
            label="gitlab.com",
            icon="apps/webauthn/res/icon_gitlab.toif",
            use_sign_count=None,
            use_self_attestation=None,
        )
    elif rp_id_hash == b"\xa5\x46\x72\xb2\x22\xc4\xcf\x95\xe1\x51\xed\x8d\x4d\x3c\x76\x7a\x6c\xc3\x49\x43\x59\x43\x79\x4e\x88\x4f\x3d\x02\x3a\x82\x29\xfd":
        # U2F key for Google
        return FIDOApp(
            label="google.com",
            icon="apps/webauthn/res/icon_google.toif",
            use_sign_count=None,
            use_self_attestation=None,
        )
    elif rp_id_hash == b"\xd4\xc9\xd9\x02\x73\x26\x27\x1a\x89\xce\x51\xfc\xaf\x32\x8e\xd6\x73\xf1\x7b\xe3\x34\x69\xff\x97\x9e\x8a\xb8\xdd\x50\x1e\x66\x4f":
        # WebAuthn key for Google
        return FIDOApp(
            label="google.com",
            icon="apps/webauthn/res/icon_google.toif",
            use_sign_count=None,
            use_self_attestation=None,
        )
    elif rp_id_hash == b"\x53\xa1\x5b\xa4\x2a\x7c\x03\x25\xb8\xdb\xee\x28\x96\x34\xa4\x8f\x58\xae\xa3\x24\x66\x45\xd5\xff\x41\x8f\x9b\xb8\x81\x98\x85\xa9":
        # U2F key for Keeper
        return FIDOApp(
            label="keepersecurity.com",
            icon="apps/webauthn/res/icon_keeper.toif",
            use_sign_count=None,
            use_self_attestation=None,
        )
    elif rp_id_hash == b"\xd6\x5f\x00\x5e\xf4\xde\xa9\x32\x0c\x99\x73\x05\x3c\x95\xff\x60\x20\x11\x5d\x5f\xec\x1b\x7f\xee\x41\xa5\x78\xe1\x8d\xf9\xca\x8c":
        # U2F key for Keeper
        return FIDOApp(
            label="keepersecurity.eu",
            icon="apps/webauthn/res/icon_keeper.toif",
            use_sign_count=None,
            use_self_attestation=None,
        )
    elif rp_id_hash == b"\xf8\x3f\xc3\xa1\xb2\x89\xa0\xde\xc5\xc1\xc8\xaa\x07\xe9\xb5\xdd\x9c\xbb\x76\xf6\xb2\xf5\x60\x60\x17\x66\x72\x68\xe5\xb9\xc4\x5e":
        # WebAuthn key for login.gov
        return FIDOApp(
            label="secure.login.gov",
            icon="apps/webauthn/res/icon_login.gov.toif",
            use_sign_count=False,
            use_self_attestation=None,
        )
    elif rp_id_hash == b"\x35\x6c\x9e\xd4\xa0\x93\x21\xb9\x69\x5f\x1e\xaf\x91\x82\x03\xf1\xb5\x5f\x68\x9d\xa6\x1f\xbc\x96\x18\x4c\x15\x7d\xda\x68\x0c\x81":
        # WebAuthn key for Microsoft
        return FIDOApp(
            label="login.microsoft.com",
            icon="apps/webauthn/res/icon_microsoft.toif",
            use_sign_count=False,
            use_self_attestation=False,
        )
    elif rp_id_hash == b"\xab\x2d\xaf\x07\x43\xde\x78\x2a\x70\x18\x9a\x0f\x5e\xfc\x30\x90\x2f\x92\x5b\x9f\x9a\x18\xc5\xd7\x14\x1b\x7b\x12\xf8\xa0\x10\x0c":
        # WebAuthn key for mojeID
        return FIDOApp(
            label="mojeid.cz",
            icon="apps/webauthn/res/icon_mojeid.toif",
            use_sign_count=None,
            use_self_attestation=None,
        )
    elif rp_id_hash == b"\x08\xb2\xa3\xd4\x19\x39\xaa\x31\x66\x84\x93\xcb\x36\xcd\xcc\x4f\x16\xc4\xd9\xb4\xc8\x23\x8b\x73\xc2\xf6\x72\xc0\x33\x00\x71\x97":
        # U2F key for Slush Pool
        return FIDOApp(
            label="slushpool.com",
            icon="apps/webauthn/res/icon_slushpool.toif",
            use_sign_count=None,
            use_self_attestation=None,
        )
    elif rp_id_hash == b"\x38\x80\x4f\x2e\xff\x74\xf2\x28\xb7\x41\x51\xc2\x01\xaa\x82\xe7\xe8\xee\xfc\xac\xfe\xcf\x23\xfa\x14\x6b\x13\xa3\x76\x66\x31\x4f":
        # U2F key for Slush Pool
        return FIDOApp(
            label="slushpool.com",
            icon="apps/webauthn/res/icon_slushpool.toif",
            use_sign_count=None,
            use_self_attestation=None,
        )
    elif rp_id_hash == b"\x2a\xc6\xad\x09\xa6\xd0\x77\x2c\x44\xda\x73\xa6\x07\x2f\x9d\x24\x0f\xc6\x85\x4a\x70\xd7\x9c\x10\x24\xff\x7c\x75\x59\x59\x32\x92":
        # U2F key for Stripe
        return FIDOApp(
            label="stripe.com",
            icon="apps/webauthn/res/icon_stripe.toif",
            use_sign_count=None,
            use_self_attestation=None,
        )
    elif rp_id_hash == b"\xfa\xbe\xec\xe3\x98\x2f\xad\x9d\xdc\xc9\x8f\x91\xbd\x2e\x75\xaf\xc7\xd1\xf4\xca\x54\x49\x29\xb2\xd0\xd0\x42\x12\xdf\xfa\x30\xfa":
        # U2F key for Tutanota
        return FIDOApp(
            label="tutanota.com",
            icon="apps/webauthn/res/icon_tutanota.toif",
            use_sign_count=None,
            use_self_attestation=None,
        )
    elif rp_id_hash == b"\x1b\x3c\x16\xdd\x2f\x7c\x46\xe2\xb4\xc2\x89\xdc\x16\x74\x6b\xcc\x60\xdf\xcf\x0f\xb8\x18\xe1\x32\x15\x52\x6e\x14\x08\xe7\xf4\x68":
        # U2F key for u2f.bin.coffee
        return FIDOApp(
            label="u2f.bin.coffee",
            icon=None,
            use_sign_count=None,
            use_self_attestation=None,
        )
    elif rp_id_hash == b"\xa6\x42\xd2\x1b\x7c\x6d\x55\xe1\xce\x23\xc5\x39\x98\x28\xd2\xc7\x49\xbf\x6a\x6e\xf2\xfe\x03\xcc\x9e\x10\xcd\xf4\xed\x53\x08\x8b":
        # WebAuthn key for webauthn.bin.coffee
        return FIDOApp(
            label="webauthn.bin.coffee",
            icon=None,
            use_sign_count=None,
            use_self_attestation=None,
        )
    elif rp_id_hash == b"\x74\xa6\xea\x92\x13\xc9\x9c\x2f\x74\xb2\x24\x92\xb3\x20\xcf\x40\x26\x2a\x94\xc1\xa9\x50\xa0\x39\x7f\x29\x25\x0b\x60\x84\x1e\xf0":
        # WebAuthn key for WebAuthn.io
        return FIDOApp(
            label="webauthn.io",
            icon=None,
            use_sign_count=None,
            use_self_attestation=None,
        )
    elif rp_id_hash == b"\xf9\x5b\xc7\x38\x28\xee\x21\x0f\x9f\xd3\xbb\xe7\x2d\x97\x90\x80\x13\xb0\xa3\x75\x9e\x9a\xea\x3d\x0a\xe3\x18\x76\x6c\xd2\xe1\xad":
        # WebAuthn key for WebAuthn.me
        return FIDOApp(
            label="webauthn.me",
            icon=None,
            use_sign_count=None,
            use_self_attestation=None,
        )
    elif rp_id_hash == b"\xc4\x6c\xef\x82\xad\x1b\x54\x64\x77\x59\x1d\x00\x8b\x08\x75\x9e\xc3\xe6\xd2\xec\xb4\xf3\x94\x74\xbf\xea\x69\x69\x92\x5d\x03\xb7":
        # WebAuthn key for demo.yubico.com
        return FIDOApp(
            label="demo.yubico.com",
            icon=None,
            use_sign_count=None,
            use_self_attestation=None,
        )
    else:
        return None
