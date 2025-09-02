//! generated from ${THIS_FILE.name}
//! (by running `make templates` in `core`)
//! do not edit manually!

#![cfg_attr(rustfmt, rustfmt_skip)]
<%
import json
import re

TR_DIR = ROOT / "core" / "translations"

order_file = TR_DIR / "order.json"
order_index_name = json.loads(order_file.read_text())
order = {int(k): v for k, v in order_index_name.items()}
assert list(order) == sorted(order)


en_file = TR_DIR / "en.json"
en_data = json.loads(en_file.read_text())["translations"]

def encode_str(s):
    return re.sub(r'\\u([0-9a-f]{4})', r'\\u{\g<1>}', json.dumps(s))

def make_cfg(name):
    if any(name.startswith(prefix + "__") for prefix in ALTCOIN_PREFIXES):
        yield '#[cfg(feature = "universal_fw")]'

    if any(name.startswith(prefix + "__") for prefix in DEBUG_PREFIXES):
        yield '#[cfg(feature = "debug")]'

en_items = [(idx, name) for idx, name in order.items() if name in en_data]
en_names = [name for _, name in en_items]
sorted_en_names = sorted(en_names)  # sorted by Qstr identifier

%>\
#[cfg(feature = "micropython")]
use crate::micropython::qstr::Qstr;

#[derive(Copy, Clone, FromPrimitive, PartialEq, Eq, PartialOrd, Ord)]
#[cfg_attr(feature = "debug", derive(ufmt::derive::uDebug))]
#[cfg_attr(test, derive(Debug))]
#[repr(u16)]
#[allow(non_camel_case_types)]
pub enum TranslatedString {
% for idx, name in en_items:
% for cfg_line in make_cfg(name):
    ${cfg_line}
% endfor
    ${name} = ${idx},  // ${encode_str(en_data.get(name))}
% endfor
}

impl TranslatedString {
    pub const DATA_MAP: &'static [(Self, &'static str)] = &[
% for name in en_names:
<%
            value = en_data[name]
            layouts_dict = value if isinstance(value, dict) else None
%>\
%if layouts_dict is not None:
    % for layout_name, layout_value in layouts_dict.items():
        % for cfg_line in make_cfg(name):
            ${cfg_line}
        % endfor
            #[cfg(feature = "${f"layout_{layout_name.lower()}"}")]
            (Self::${name}, ${encode_str(layout_value)}),
    % endfor
%else:
        % for cfg_line in make_cfg(name):
            ${cfg_line}
        % endfor
            (Self::${name}, ${encode_str(value)}),
%endif
% endfor
    ];

    #[cfg(feature = "micropython")]
    pub const QSTR_MAP: &'static [(Qstr, Self)] = &[
% for name in sorted_en_names:
    % for cfg_line in make_cfg(name):
        ${cfg_line}
    % endfor
        (Qstr::MP_QSTR_${name}, Self::${name}),
%endfor
    ];
}
