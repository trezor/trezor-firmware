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

%>\
class TR:
% for name, text in sorted(en_data.items()):
    ${name}: str = ${json.dumps(text)}
% endfor

