//! generated from en.rs.mako
//! (by running `make templates` in `core`)
//! do not edit manually!

<%
import json

from pathlib import Path

THIS = Path(local.filename).resolve()
SRCDIR = THIS.parent

file = SRCDIR / "en.json"

data = json.loads(file.read_text())["translations"]
items_to_write: list[tuple[str, str]] = []
for section_name, section in data.items():
    for k, v in section.items():
        name = f"{section_name}__{k}"
        items_to_write.append((name, v))
items_to_write.sort(key=lambda x: x[0])
%>\
use super::general::TranslationsGeneral;

#[rustfmt::skip]
pub const EN_TRANSLATIONS: TranslationsGeneral = TranslationsGeneral {
% for k, v in items_to_write:
    ${k}: ${utf8_str(v)},
% endfor
};
