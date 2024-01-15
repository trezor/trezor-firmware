# generated from trezortranslate_keys.pyi.mako
# (by running `make templates` in `core`)
# do not edit manually!
<%
import json
from pathlib import Path

THIS = Path(local.filename).resolve()
CORE_DIR = THIS.parent.parent

en_file = CORE_DIR / "embed" / "rust" / "src" / "translations" / "en.json"
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
class TR:
% for name, text in sorted(en_strings.items()):
    ${name}: str = ${text}
% endfor

