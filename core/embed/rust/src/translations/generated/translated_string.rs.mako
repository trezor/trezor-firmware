//! generated from ${THIS_FILE.name}
//! (by running `make templates` in `core`)
//! do not edit manually!

#![cfg_attr(rustfmt, rustfmt_skip)]
<%
import itertools
import json
import re

from trezorlib._internal.translations import TranslatedStringsChunk

TR_DIR = ROOT / "core" / "translations"

order_file = TR_DIR / "order.json"
order_index_name = json.loads(order_file.read_text())
order = {int(k): v for k, v in order_index_name.items()}
assert list(order) == sorted(order)


en_file = TR_DIR / "en.json"
en_data = json.loads(en_file.read_text())["translations"]

def encode_str(s: str) -> str:
    return re.sub(r'\\u([0-9a-f]{4})', r'\\u{\g<1>}', json.dumps(s))

def is_altcoin(name):
    return any(name.startswith(prefix + "__") for prefix in ALTCOIN_PREFIXES)

def is_debug(name):
    return any(name.startswith(prefix + "__") for prefix in DEBUG_PREFIXES)

def is_btc_only(name):
    return not (is_altcoin(name) or is_debug(name))

layout_names = set()
for v in en_data.values():
    if isinstance(v, dict):
        layout_names.update(v.keys())
# Assume all layout names appear as keys at `en.json`
assert layout_names

def use_layout(s: str | dict[str, str], layout_name: str | None = None) -> str:
    if isinstance(s, dict) and layout_name is not None:
        s = s[layout_name]
    return s

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
    cfg_if::cfg_if! {
% for i, layout_name in enumerate(sorted(layout_names)):
        ${"if" if i == 0 else "} else if"} #[cfg(feature = "layout_${layout_name.lower()}")] {
<%
# English words for this layout (may include "" for unused/deprecated entries)
layout_data = [use_layout(en_data.get(name, ""), layout_name) for name in order.values()]

def filter_by_features(values: list[str], keep_debug: bool, keep_altcoin: bool) -> list[str]:
    # Unused strings are mapped to ""
    def filter_value(value) -> str:
        if is_altcoin(value) and not keep_altcoin:
            return ""
        if is_debug(value) and not keep_debug:
            return ""
        return value
    return [filter_value(value) for value in values]

%>\
% for enabled_features in itertools.product([True, False], repeat=2):
<%
    features = [f'feature = "{s}"' for s in ["debug", "universal_fw"]]
    configs = [
        feature if is_enabled else f'not({feature})'
        for is_enabled, feature in zip(enabled_features, features)
    ]
    cfg_line = f'#[cfg(all({', '.join(configs)}))]'

    # Currently all English words fit into a single chunk
    [encoded] = TranslatedStringsChunk.from_items(filter_by_features(layout_data, *enabled_features))
%>\
            ${cfg_line}
            pub const ENGLISH_STRINGS: &'static str = ${encode_str(encoded.strings.decode())};
            ${cfg_line}
            pub const ENGLISH_OFFSETS: &'static [u16] = &${encoded.offsets};

% endfor
% endfor
        }
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
