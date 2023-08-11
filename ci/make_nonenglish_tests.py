from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

HERE = Path(__file__).resolve().parent

TEST_FILE = HERE / "test-nonenglish.yml"

LANGS = {
    "cs": "czech",
    "fr": "french",
    "de": "german",
    "es": "spanish",
}

MODELS = ["T", "R"]


@dataclass
class Replacement:
    start: str
    end: str
    replacement: str


def replace_content_between_markers(
    file_path: Path | str, replacements: list[Replacement]
) -> None:
    with open(file_path, "r") as file:
        content = file.read()

    for replace in replacements:
        pattern = rf"({replace.start}.*?{replace.end})"
        content = re.sub(
            pattern,
            f"{replace.start}\n{replace.replacement}\n{replace.end}",
            content,
            flags=re.DOTALL,
        )

    with open(file_path, "w") as file:
        file.write(content)


def get_device_test(lang: str, model: str) -> str:
    lang_long = LANGS[lang]

    model_or_empty = f" {model}" if model != "T" else ""
    model_needs_or_empty = f" {model}" if model != "T" else ""

    return f"""\
core device{model_or_empty} test {lang_long}:
  stage: test
  <<: *gitlab_caching
  needs:
    - core unix frozen{model_needs_or_empty} debug build
  variables:
    TREZOR_PROFILING: "1"  # so that we get coverage data
    TREZOR_MODEL: "{model}"
    MULTICORE: "4"  # more could interfere with other jobs
    TEST_LANG: "{lang}"  # {lang_long}
  only:
    - schedules  # nightly build
    - /translations/  # translations branches
  script:
    - $NIX_SHELL --run "poetry run make -C core test_emu_ui_multicore | ts -s"
  after_script:
    - mv core/src/.coverage.* core  # there will be more coverage files (one per core)
    - mv tests/ui_tests/reports/test/ test_ui_report
    - $NIX_SHELL --run "poetry run python ci/prepare_ui_artifacts.py | ts -s"
    - diff -u tests/ui_tests/fixtures.json tests/ui_tests/fixtures.suggestion.json
  artifacts:
    name: "$CI_JOB_NAME-$CI_COMMIT_SHORT_SHA"
    paths:
      - ci/ui_test_records/
      - test_ui_report
      - tests/ui_tests/screens/
      - tests/ui_tests/fixtures.suggestion.json
      - tests/ui_tests/fixtures.results.json
      - tests/junit.xml
      - tests/trezor.log
      - core/.coverage.*
    when: always
    expire_in: 1 week
    reports:
      junit: tests/junit.xml
"""


def get_click_test(lang: str, model: str) -> str:
    lang_long = LANGS[lang]

    model_or_empty = f" {model}" if model != "T" else ""
    model_needs_or_empty = f" {model}" if model != "T" else ""

    return f"""\
core click{model_or_empty} test {lang_long}:
  stage: test
  <<: *gitlab_caching
  needs:
    - core unix frozen{model_needs_or_empty} debug build
  variables:
    TREZOR_PROFILING: "1"  # so that we get coverage data
    TREZOR_MODEL: "{model}"
    TEST_LANG: "{lang}"  # {lang_long}
  only:
    - schedules  # nightly build
    - /translations/  # translations branches
  script:
    - $NIX_SHELL --run "poetry run make -C core test_emu_click_ui | ts -s"
  after_script:
    - mv core/src/.coverage core/.coverage.test_click
    - mv tests/ui_tests/reports/test/ test_ui_report
    - $NIX_SHELL --run "poetry run python ci/prepare_ui_artifacts.py | ts -s"
    - diff -u tests/ui_tests/fixtures.json tests/ui_tests/fixtures.suggestion.json
  artifacts:
    name: "$CI_JOB_NAME-$CI_COMMIT_SHORT_SHA"
    paths:
      - ci/ui_test_records/
      - test_ui_report
      - tests/ui_tests/screens/
      - tests/ui_tests/fixtures.suggestion.json
      - tests/ui_tests/fixtures.results.json
      - tests/trezor.log
      - tests/junit.xml
      - core/.coverage.*
    reports:
      junit: tests/junit.xml
    expire_in: 1 week
    when: always
"""


def get_all_tests_text(func: Callable[[str, str], str]) -> str:
    text = ""
    for model in MODELS:
        for lang in LANGS:
            content = func(lang, model)
            text += content + "\n"
    return text


def fill_device_tests() -> None:
    replacement = Replacement(
        start=r"##START_DEVICE_TESTS",
        end=r"##END_DEVICE_TESTS",
        replacement=get_all_tests_text(get_device_test),
    )
    replace_content_between_markers(TEST_FILE, [replacement])


def fill_click_tests() -> None:
    replacement = Replacement(
        start=r"##START_CLICK_TESTS",
        end=r"##END_CLICK_TESTS",
        replacement=get_all_tests_text(get_click_test),
    )
    replace_content_between_markers(TEST_FILE, [replacement])


if __name__ == "__main__":
    fill_device_tests()
    fill_click_tests()
