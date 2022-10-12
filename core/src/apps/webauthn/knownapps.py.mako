# generated from knownapps.py.mako
# (by running `make templates` in `core`)
# do not edit manually!

# NOTE: using positional arguments saves 520 bytes in flash space


class FIDOApp:
    def __init__(
        self,
        label: str,
        icon_name: str | None,
        use_sign_count: bool | None,
        use_self_attestation: bool | None,
    ) -> None:
        self.label = label
        self.icon_name = icon_name
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
        app.icon_name = app.key
    else:
        app.icon_name = None
%>\
# fmt: off
def by_rp_id_hash(rp_id_hash: bytes) -> FIDOApp | None:
% for label, rp_id_hash, type, app in fido_entries:
    if rp_id_hash == ${black_repr(rp_id_hash)}:
        # ${type} key for ${app.name}
        return FIDOApp(
            ${black_repr(label)},  # label
            ${black_repr(app.icon_name)},  # icon_name
            ${black_repr(app.use_sign_count)},  # use_sign_count
            ${black_repr(app.use_self_attestation)},  # use_self_attestation
        )
% endfor

    return None
