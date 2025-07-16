import json
import sys

(RUN_ID, LANGS_JSON) = sys.argv[1:]
MAIN, *EXTRA = json.loads(LANGS_JSON)

REPORT_URL = f"https://data.trezor.io/dev/firmware/ui_report/{RUN_ID}"
CI_RUN_URL = f"https://github.com/trezor/trezor-firmware/actions/runs/{RUN_ID}"
TEST_TYPES = ["device_test", "click_test", "persistence_test"]
MODELS = [
    "T2T1",
    "T3B1",
    "T3T1",
    "T3W1",
]


def main():
    # a special marker for finding this comment (via CI)
    print("<!-- ui-comment-Core -->")
    print_table(MAIN)
    if EXTRA:
        print("\n<details>\n<summary>Translations</summary>")
        for lang in sorted(EXTRA):
            print_table(lang)
        print("\n</details>")

    print(f"\nLatest CI run: [{RUN_ID}]({CI_RUN_URL})")


def print_table(lang):
    main = f"[main]({REPORT_URL}/{lang}_index.html)"
    screens = f"[all]({REPORT_URL}/{lang}_diff.html)"
    print(f"\n# `{lang}` {main}({screens})\n")

    # Currently, persistence_test is not running with translations
    test_types = TEST_TYPES if lang == "en" else TEST_TYPES[:-1]

    header = ["model"] + test_types
    print("|".join(header))
    print("|".join(["-"] * len(header)))

    for model in MODELS:
        row = [f"{model}"]
        for test_type in test_types:
            test_prefix = f"{REPORT_URL}/{model}-{lang}-core_{test_type}"

            job_img = f'<img src="{test_prefix}-status.png"/>'

            test_diff = f"[test]({test_prefix}-index.html)"
            test_screens = f"[all]({test_prefix}-differing_screens.html)"
            test_img = f'<img src="{test_prefix}-test_diff.png"/>'

            main_diff = f"[main]({test_prefix}-master_index.html)"
            main_screens = f"[all]({test_prefix}-master_diff.html)"
            main_img = f'<img src="{test_prefix}-main_diff.png"/>'

            cell = f"{job_img} {test_diff}({test_screens}) {test_img} {main_diff}({main_screens}) {main_img}"
            row.append(cell)

        print("|".join(row))


if __name__ == "__main__":
    main()
