//! generated from webauthn_icons.rs.mako
//! (by running `make templates` in `core`)
//! do not edit manually!

use crate::ui::display::toif::NamedToif;

<%
icons: list[tuple[str, str]] = []
for app in fido:
    if app.icon is not None:
        # Variable names cannot have a dot in themselves
        icon_name = app.key
        var_name = icon_name.replace(".", "_").upper()
        icons.append((icon_name, var_name))
%>\

% for icon_name, var_name in icons:
const ICON_${var_name}: NamedToif = NamedToif(include_res!("model_tt/res/fido/icon_${icon_name}.toif"), "${var_name}");
% endfor
/// Default icon when app does not have its own
const ICON_WEBAUTHN: NamedToif = NamedToif(include_res!("model_tt/res/fido/icon_webauthn.toif"), "WEBAUTHN");

/// Translates icon name into its data.
/// Returns default `ICON_WEBAUTHN` when the icon is not found or name not
/// supplied.
pub fn get_fido_icon_data<T: AsRef<str>>(icon_name: Option<T>) -> NamedToif {
    if let Some(icon_name) = icon_name {
        match icon_name.as_ref() {
% for icon_name, var_name in icons:
            "${icon_name}" => ICON_${var_name},
% endfor
            _ => ICON_WEBAUTHN,
        }
    } else {
        ICON_WEBAUTHN
    }
}
