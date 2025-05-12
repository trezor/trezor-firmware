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

impl TranslatedString {

% for blob_name, predicate_fn, feature in features:
    const ${blob_name}: StringsBlob = StringsBlob {
        text: concat!(
    % for name in filter(predicate_fn, en_names):
            ${encode_str(en_data[name])},
    % endfor
        ),
<%
    byte_offset = 0
%>\
        offsets: &[
    % for name in filter(predicate_fn, en_names):
<%
    byte_offset += len(en_data[name].encode())
%>\
            (Self::${name}, ${byte_offset}),
    % endfor
        ],
    };
% endfor

    pub const BLOBS: &'static [StringsBlob] = &[
% for blob_name, predicate_fn, feature in features:
        Self::${blob_name},
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
