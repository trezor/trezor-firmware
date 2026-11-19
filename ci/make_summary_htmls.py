import json
import sys

SUFFIX, LANGS_JSON, TARGET = sys.argv[1:]

LANGS = json.loads(LANGS_JSON)
# The <include> elements are replaced by the referenced pages in `testreport.js`,
# which `.github/actions/ui-report` uploads next to them. Inline scripts would be
# blocked by the Content-Security-Policy of data.trezor.io.
for lang in LANGS:
    HTML = rf"""<!DOCTYPE html>
    <html>

    <head>
        <meta charset="utf-8">
        <title>Master index</title>
        <script type="text/javascript" src="testreport.js"></script>
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

    </body>
    </html>
    """
    with open(f"{TARGET}/{lang}_{SUFFIX}.html", "w") as f:
        f.write(HTML)
