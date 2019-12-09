# generated from knownapps.py.mako
# do not edit manually!
# flake8: noqa


if False:
    from typing import Optional


class FIDOApp:
    def __init__(
        self, label: str, icon: Optional[str], use_sign_count: Optional[bool]
    ) -> None:
        self.label = label
        self.icon = icon
        self.use_sign_count = use_sign_count


<%
from hashlib import sha256

fido_entries = []
for app in fido:
    for app_id in app.u2f:
        fido_entries.append((bytes.fromhex(app_id), "U2F", app))
    for origin in app.webauthn:
        rp_id_hash = sha256(origin.encode()).digest()
        fido_entries.append((rp_id_hash, "WebAuthn", app))
    if app.icon is not None:
        app.icon_res = f"apps/webauthn/res/icon_{app.key}.toif"
    else:
        app.icon_res = None
%>\
# fmt: off
def by_rp_id_hash(rp_id_hash: bytes) -> Optional[FIDOApp]:
    if False:
        raise RuntimeError  # if false
% for rp_id_hash, type, app in fido_entries:
    elif rp_id_hash == ${black_repr(rp_id_hash)}:
        # ${type} key for ${app.label}
        return FIDOApp(
            label=${black_repr(app.label)},
            icon=${black_repr(app.icon_res)},
            use_sign_count=${black_repr(app.use_sign_count)},
        )
% endfor
    else:
        return None
