//! generated from webauthn_icons.rs.mako
//! (by running `make templates` in `core`)
//! do not edit manually!


use crate::strutil::TString;
use crate::ui::util::include_res;

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
const ICON_${var_name}: &[u8] = include_res!("layout_delizia/res/fido/icon_${icon_name}.toif");
% endfor

/// Translates icon name into its data.
pub fn get_fido_icon_data(icon_name: Option<TString<'static>>) -> Option< &'static [u8]> {
    if let Some(icon_name) = icon_name {
        icon_name.map(|c| match c {
% for icon_name, var_name in icons:
            "${icon_name}" => Some(ICON_${var_name}),
% endfor
            _ => None,
        })
    } else {
        None
    }
}
