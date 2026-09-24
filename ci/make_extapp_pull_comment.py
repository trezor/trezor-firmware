import json
import sys

RUN_ID, LANGS_JSON = sys.argv[1:]
MAIN, *EXTRA = json.loads(LANGS_JSON)

REPORT_URL = f"https://data.trezor.io/dev/firmware/ui_report/{RUN_ID}"
CI_RUN_URL = f"https://github.com/trezor/trezor-firmware/actions/runs/{RUN_ID}"
# Same columns/rows shape as ci/make_pull_comment.py (Core's own UI report
# comment), except the columns are individual extapps rather than test types
# -- there's only one test type (device tests) for extapps today.
APPS = ["tron"]
MODELS = ["t3w1"]


def main():
    # a special marker for finding this comment (via CI)
    print("<!-- ui-comment-SDK -->")
    print_table(MAIN)
    if EXTRA:
        print("\n<details>\n<summary>Translations</summary>")
        for lang in sorted(EXTRA):
            print_table(lang)
        print("\n</details>")

    print(f"\nLatest CI run: [{RUN_ID}]({CI_RUN_URL})")


def print_table(lang):
    print(f"\n# `{lang}`\n")

    header = ["model"] + APPS
    print("|".join(header))
    print("|".join(["-"] * len(header)))

    for model in MODELS:
        row = [f"{model}"]
        for app in APPS:
            # No master-branch diff column here (unlike Core's report): extapp
            # device tests don't run with --do-master-diff yet, since tron's
            # ui_tests/reporting module (sdk/apps/tron/tests/ui_tests/reporting)
            # isn't adapted for its group-less fixtures schema yet.
            test_prefix = f"{REPORT_URL}/{model}-{lang}-extapp_device_test_{app}"

            job_img = f'<img src="{test_prefix}-status.png"/>'

            test_diff = f"[test]({test_prefix}-index.html)"
            test_screens = f"[all]({test_prefix}-differing_screens.html)"
            test_img = f'<img src="{test_prefix}-test_diff.png"/>'

            cell = f"{job_img} {test_diff}({test_screens}) {test_img}"
            row.append(cell)

        print("|".join(row))


if __name__ == "__main__":
    main()
