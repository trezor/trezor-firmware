# generated from ${THIS_FILE.name}
# (by running `make templates` in `core`)
# do not edit manually!
<%
import json

en_file = ROOT / "core" / "translations" / "en.json"
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

