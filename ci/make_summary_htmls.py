import json
import sys

(SUFFIX, LANGS_JSON, TARGET) = sys.argv[1:]

LANGS = json.loads(LANGS_JSON)
for lang in LANGS:
    HTML = rf"""<!DOCTYPE html>
    <html>

    <head>
        <meta charset="utf-8">
        <title>Master index</title>
    </head>
    <body>

    <h1>T2T1</h1>
    <include src="T2T1-{lang}-core_device_test-master_{SUFFIX}.html"></include>
    <include src="T2T1-{lang}-core_click_test-master_{SUFFIX}.html"></include>
    <include src="T2T1-{lang}-core_persistence_test-master_{SUFFIX}.html"></include>

    <h1>T3B1</h1>
    <include src="T3B1-{lang}-core_device_test-master_{SUFFIX}.html"></include>
    <include src="T3B1-{lang}-core_click_test-master_{SUFFIX}.html"></include>
    <include src="T3B1-{lang}-core_persistence_test-master_{SUFFIX}.html"></include>

    <h1>T3T1</h1>
    <include src="T3T1-{lang}-core_device_test-master_{SUFFIX}.html"></include>
    <include src="T3T1-{lang}-core_click_test-master_{SUFFIX}.html"></include>
    <include src="T3T1-{lang}-core_persistence_test-master_{SUFFIX}.html"></include>

    <h1>T3W1</h1>
    <include src="T3W1-{lang}-core_device_test-master_{SUFFIX}.html"></include>
    <include src="T3W1-{lang}-core_click_test-master_{SUFFIX}.html"></include>
    <include src="T3W1-{lang}-core_persistence_test-master_{SUFFIX}.html"></include>

    <script>
    (() => {{
        const includes = document.getElementsByTagName('include');
        [].forEach.call(includes, i => {{
            let filePath = i.getAttribute('src');
            fetch(filePath).then(file => {{
                file.text().then(content => {{
                    i.insertAdjacentHTML('afterend', content);
                    i.remove();
                }});
            }});
        }});
    }})();
    </script>

    </body>
    </html>
    """
    with open(f"{TARGET}/{lang}_{SUFFIX}.html", "w") as f:
        f.write(HTML)
