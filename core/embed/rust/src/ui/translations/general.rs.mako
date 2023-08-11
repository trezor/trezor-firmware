//! generated from cs.rs.mako
//! (by running `make templates` in `core`)
//! do not edit manually!

<%
import json
from pathlib import Path

THIS = Path(local.filename).resolve()
SRCDIR = THIS.parent

order_file = SRCDIR / "order.json"
order_index_name = json.loads(order_file.read_text())
order_name_index = {v: int(k) for k, v in order_index_name.items()}

en_file = SRCDIR / "en.json"
en_data = json.loads(en_file.read_text())["translations"]

def get_all_json_keys(data: dict) -> set[str]:
    keys: set[str] = set()
    for section_name, section in data.items():
        for k, v in section.items():
            keys.add(f"{section_name}__{k}")
    return keys

en_keys = get_all_json_keys(en_data)

keys_index_mapping: dict[str, int] = {}
for key in en_keys:
    if key not in order_name_index:
        raise ValueError(f"key {key} not found in order.json")
    keys_index_mapping[key] = order_name_index[key]

index_sorted_keys = sorted(keys_index_mapping.items(), key=lambda x: x[1])
%>\
#[rustfmt::skip]
#[allow(non_snake_case)]
pub struct TranslationsGeneral {
% for name, _ in index_sorted_keys:
    pub ${name}: &'static str,
% endfor
}

#[rustfmt::skip]
impl TranslationsGeneral {
    pub fn get_text(&self, key: &str) -> Option<<&'static str> {
        self.get_info(key).map(|(text, _)| text)
    }

    pub fn get_position(&self, key: &str) -> Option<usize> {
        self.get_info(key).map(|(_, pos)| pos)
    }

    fn get_info(&self, key: &str) -> Option<(&'static str, usize)> {
        match key {
% for name, index in index_sorted_keys:
            ${utf8_str(name)} => Some((self.${name}, ${index})),
% endfor
            _ => None,
        }
    }
}
