# generated from ${THIS_FILE.name}
# (by running `make templates` in `core`)
# do not edit manually!
<%
import json

en_file = ROOT / "core" / "translations" / "en.json"
en_data = json.loads(en_file.read_text())["translations"]

%>\
class TR:
% for name, text in sorted(en_data.items()):
    ${name}: str = ${json.dumps(text)}
% endfor

