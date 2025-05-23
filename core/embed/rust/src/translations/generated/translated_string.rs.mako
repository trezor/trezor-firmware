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

layout_names = set()
for v in en_data.values():
    if isinstance(v, dict):
        layout_names.update(v.keys())
# Assume all layout names appear as keys at `en.json`
assert layout_names

def encode_str(s, layout_name=None):
    if isinstance(s, dict) and layout_name is not None:
        s = s[layout_name]
    return re.sub(r'\\u([0-9a-f]{4})', r'\\u{\g<1>}', json.dumps(s))

def byte_size_str(s, layout_name):
    if isinstance(s, dict):
        s = s[layout_name]
    return len(s.encode())

def is_altcoin(name):
    return any(name.startswith(prefix + "__") for prefix in ALTCOIN_PREFIXES)

def is_debug(name):
    return any(name.startswith(prefix + "__") for prefix in DEBUG_PREFIXES)

def is_btc_only(name):
    return not (is_altcoin(name) or is_debug(name))

def make_cfg(name):
    if any(name.startswith(prefix + "__") for prefix in ALTCOIN_PREFIXES):
        yield '#[cfg(feature = "universal_fw")]'

    if any(name.startswith(prefix + "__") for prefix in DEBUG_PREFIXES):
        yield '#[cfg(feature = "debug")]'

en_items = [(idx, name) for idx, name in order.items() if name in en_data]
en_names = [name for _, name in en_items]
sorted_en_names = sorted(en_names)  # sorted by Qstr identifier

features = (
    ("BTC_ONLY_BLOB", is_btc_only, None),
    ("ALTCOIN_BLOB", is_altcoin, "universal_fw"),
    ("DEBUG_BLOB", is_debug, "debug"),
)

%>\
#[cfg(feature = "micropython")]
use crate::micropython::qstr::Qstr;

pub struct StringsBlob {
    pub text: &'static str,
    pub offsets: &'static [(TranslatedString, u16)],
}

#[derive(Copy, Clone, FromPrimitive, PartialEq, Eq, PartialOrd, Ord)]
#[cfg_attr(feature = "debug", derive(ufmt::derive::uDebug))]
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

cfg_if::cfg_if! {
% for i, layout_name in enumerate(sorted(layout_names)):
    ${"if" if i == 0 else "} else if"} #[cfg(feature = "layout_${layout_name.lower()}")] {
        impl TranslatedString {
        % for blob_name, predicate_fn, feature in features:
            % if feature is not None:
            #[cfg(feature = "${feature}")]
            % endif
            const ${blob_name}: StringsBlob = StringsBlob {
                text: concat!(
            % for name in filter(predicate_fn, en_names):
                    ${encode_str(en_data[name], layout_name)},
            % endfor
                ),
<%
byte_offset = 0
%>\
                offsets: &[
            % for name in filter(predicate_fn, en_names):
<%
byte_offset += byte_size_str(en_data[name], layout_name)
%>\
                    (Self::${name}, ${byte_offset}),
            % endfor
                ],
            };

        % endfor
            pub const BLOBS: &'static [StringsBlob] = &[
        % for blob_name, predicate_fn, feature in features:
                % if feature is not None:
                #[cfg(feature = "${feature}")]
                % endif
                Self::${blob_name},
        % endfor
            ];
        }
% endfor
    }
}

#[cfg(feature = "micropython")]
impl TranslatedString {
    pub const QSTR_MAP: &'static [(Qstr, Self)] = &[
% for name in sorted_en_names:
    % for cfg_line in make_cfg(name):
        ${cfg_line}
    % endfor
        (Qstr::MP_QSTR_${name}, Self::${name}),
%endfor
    ];
}
