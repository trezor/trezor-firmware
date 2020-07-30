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


<%
from hashlib import sha256

fido_entries = []
for app in fido:
    for u2f in app.u2f:
        fido_entries.append((u2f["label"], bytes.fromhex(u2f["app_id"]), "U2F", app))
    for origin in app.webauthn:
        rp_id_hash = sha256(origin.encode()).digest()
        fido_entries.append((origin, rp_id_hash, "WebAuthn", app))
    if app.icon is not None:
        app.icon_res = f"apps/webauthn/res/icon_{app.key}.toif"
    else:
        app.icon_res = None
%>\
# fmt: off
def by_rp_id_hash(rp_id_hash: bytes) -> Optional[FIDOApp]:
    if False:
        raise RuntimeError  # if false
% for label, rp_id_hash, type, app in fido_entries:
    elif rp_id_hash == ${black_repr(rp_id_hash)}:
        # ${type} key for ${app.name}
        return FIDOApp(
            label=${black_repr(label)},
            icon=${black_repr(app.icon_res)},
            use_sign_count=${black_repr(app.use_sign_count)},
            use_self_attestation=${black_repr(app.use_self_attestation)},
        )
% endfor
    else:
        return None
