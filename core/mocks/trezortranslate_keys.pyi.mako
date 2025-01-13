# generated from ${THIS_FILE.name}
# (by running `make templates` in `core`)
# do not edit manually!
<%
import json

en_file = ROOT / "core" / "translations" / "en.json"
en_data = json.loads(en_file.read_text())["translations"]

%>\
class TR:
% for name, value in sorted(en_data.items()):
<%
    if isinstance(value, dict):
        # For simplicity, use the first model's text for the stubs.
        value, *_ = value.values()
%>\
    ${name}: str = ${json.dumps(value)}
% endfor

