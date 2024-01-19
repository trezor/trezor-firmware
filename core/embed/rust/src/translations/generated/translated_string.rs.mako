//! generated from ${THIS_FILE.name}
//! (by running `make templates` in `core`)
//! do not edit manually!
<%
import json

TR_DIR = ROOT / "core" / "translations"

order_file = TR_DIR / "order.json"
order_index_name = json.loads(order_file.read_text())
order = {int(k): v for k, v in order_index_name.items()}


en_file = TR_DIR / "en.json"
en_data = json.loads(en_file.read_text())["translations"]

def get_en_strings(data: dict) -> dict[str, str]:
    res = {}
    for section_name, section in data.items():
        for k, v in section.items():
            key = f"{section_name}__{k}"
            res[key] = json.dumps(v)
    return res

en_strings = get_en_strings(en_data)

%>\
#[cfg(feature = "micropython")]
use crate::micropython::qstr::Qstr;

#[derive(Debug, Copy, Clone, FromPrimitive)]
#[repr(u16)]
#[rustfmt::skip]
#[allow(non_camel_case_types)]
pub enum TranslatedString {
% for idx, name in order.items():
    ${name} = ${idx},
% endfor
}

impl TranslatedString {
    pub fn untranslated(self) -> &'static str {
        match self {
% for name in order.values():
            Self::${name} => ${en_strings.get(name, '""')},
% endfor
        }
    }

    #[cfg(feature = "micropython")]
    pub fn from_qstr(qstr: Qstr) -> Option<Self> {
        match qstr {
% for name in order.values():
            Qstr::MP_QSTR_${name} => Some(Self::${name}),
% endfor
            _ => None,
        }
    }
}
