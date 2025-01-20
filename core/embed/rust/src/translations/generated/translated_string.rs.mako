//! generated from ${THIS_FILE.name}
//! (by running `make templates` in `core`)
//! do not edit manually!

#![cfg_attr(rustfmt, rustfmt_skip)]
<%
import json
import re

ALTCOIN_PREFIXES = (
    "binance",
    "cardano",
    "eos",
    "ethereum",
    "fido",
    "monero",
    "nem",
    "ripple",
    "solana",
    "stellar",
    "tezos",
    "u2f",
)

TR_DIR = ROOT / "core" / "translations"

order_file = TR_DIR / "order.json"
order_index_name = json.loads(order_file.read_text())
order = {int(k): v for k, v in order_index_name.items()}


en_file = TR_DIR / "en.json"
en_data = json.loads(en_file.read_text())["translations"]

def encode_str(s):
    return re.sub(r'\\u([0-9a-f]{4})', r'\\u{\g<1>}', json.dumps(s))

%>\
#[cfg(feature = "micropython")]
use crate::micropython::qstr::Qstr;

#[derive(Copy, Clone, FromPrimitive, PartialEq, Eq)]
#[cfg_attr(feature = "debug", derive(ufmt::derive::uDebug))]
#[repr(u16)]
#[allow(non_camel_case_types)]
pub enum TranslatedString {
% for idx, name in order.items():
    %if any(name.startswith(prefix + "__") for prefix in ALTCOIN_PREFIXES):
    #[cfg(feature = "universal_fw")]
    %endif
    ${name} = ${idx},  // ${json.dumps(en_data.get(name, '""'))}
% endfor
}

impl TranslatedString {
    // Allow building with `--all-features` (enabling all layouts results in duplicate match keys) for clippy
    #[allow(unreachable_patterns)]
    pub fn untranslated(self) -> &'static str {
        match self {
% for name in order.values():
<%
            value = en_data.get(name, '""')
            layouts_dict = value if isinstance(value, dict) else None
            universal_fw = any(name.startswith(prefix + "__") for prefix in ALTCOIN_PREFIXES)
%>\
%if layouts_dict is not None:
    % for layout_name, layout_value in layouts_dict.items():
        %if universal_fw:
            #[cfg(feature = "universal_fw")]
        %endif
            #[cfg(feature = "${f"layout_{layout_name.lower()}"}")]
            Self::${name} => ${encode_str(layout_value)},
    % endfor
%else:
    %if universal_fw:
            #[cfg(feature = "universal_fw")]
    %endif
            Self::${name} => ${encode_str(value)},
%endif
% endfor
        }
    }

    #[cfg(feature = "micropython")]
    pub fn from_qstr(qstr: Qstr) -> Option<Self> {
        match qstr {
% for name in order.values():
            %if any(name.startswith(prefix + "__") for prefix in ALTCOIN_PREFIXES):
            #[cfg(feature = "universal_fw")]
            %endif
            Qstr::MP_QSTR_${name} => Some(Self::${name}),
% endfor
            _ => None,
        }
    }
}
