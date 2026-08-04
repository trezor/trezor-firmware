from __future__ import annotations

import hashlib
import json
import re
import shutil
import typing as t
import warnings
from copy import deepcopy
from dataclasses import asdict, dataclass, field, replace
from difflib import SequenceMatcher
from functools import cached_property
from itertools import zip_longest
from pathlib import Path

import pytest
from PIL import Image
from typing_extensions import Self

from trezorlib.debuglink import TrezorTestContext as Client

UI_TESTS_DIR = Path(__file__).resolve().parent
SCREENS_DIR = UI_TESTS_DIR / "screens"
IMAGES_DIR = SCREENS_DIR / "all_images"
FIXTURES_FILE = UI_TESTS_DIR / "fixtures.json"

# fixtures.json are structured as follows:
# {
#   "model": {
#       "model_language-test_name": "hash",
#       ...
#   },
#   ...
# }
# IOW, FixturesType = dict[<model>, dict[<fixtures_name>, <hash>]]
FixturesType = t.NewType("FixturesType", dict[str, dict[str, str]])

FIXTURES: FixturesType = FixturesType({})
_FIXTURE_KEY_RE = re.compile(r"^(?P<model>[^_]+)_(?P<language>[^-]+)-(?P<name>.+)$")


def get_current_fixtures() -> FixturesType:
    global FIXTURES
    if not FIXTURES and FIXTURES_FILE.exists():
        FIXTURES = FixturesType(json.loads(FIXTURES_FILE.read_text()))
    return FIXTURES


def prepare_fixtures(
    results: t.Iterable[TestResult],
    remove_missing: bool = False,
) -> tuple[FixturesType, set[TestCase]]:
    """Prepare contents of fixtures.json."""
    grouped_tests: dict[str, dict[str, str]] = {}
    for result in results:
        model_map = grouped_tests.setdefault(result.test.model, {})
        model_map[result.test.fixtures_name] = result.actual_hash

    missing_tests: set[TestCase] = set()

    fixtures = deepcopy(get_current_fixtures())
    for model, new_content in grouped_tests.items():
        current_content = fixtures.setdefault(model, {})

        if remove_missing:
            tested_languages = {
                TestCase.get_language_from_fixture_name(name)
                for name in new_content.keys()
            }

            for key in list(current_content.keys()):
                lang = TestCase.get_language_from_fixture_name(key)
                if lang in tested_languages and key not in new_content:
                    missing_tests.add(TestCase.from_fixtures(key))
                    del current_content[key]

        current_content.update(new_content)

    return FixturesType(fixtures), missing_tests


def write_fixtures_only_new_results(
    results: t.Iterable[TestResult],
    dest: Path,
) -> None:
    """Generate new results file with only the tests that were actually run."""
    content: dict[str, dict[str, str]] = {}
    for res in results:
        model = content.setdefault(res.test.model, {})
        model[res.test.fixtures_name] = res.actual_hash
    dest.write_text(json.dumps(content, indent=0, sort_keys=True) + "\n")


def write_fixtures_complete(
    results: t.Iterable[TestResult],
    remove_missing: bool = False,
    dest: Path = FIXTURES_FILE,
) -> None:
    """Generate new fixtures.json file with all the results, updated for the latest run."""
    global FIXTURES
    content, _ = prepare_fixtures(results, remove_missing)
    dest.write_text(json.dumps(content, indent=0, sort_keys=True) + "\n")
    FIXTURES = FixturesType({})  # reset the cache


def _rename_records(screen_path: Path) -> None:
    IMAGES_DIR.mkdir(exist_ok=True)
    for index, record in enumerate(sorted(screen_path.iterdir())):
        record.replace(screen_path / f"{index:08}.png")


def screens_and_hashes(screen_path: Path) -> tuple[list[Path], list[str]]:
    if not screen_path.exists():
        return [], []

    paths: list[Path] = []
    hashes: list[str] = []
    for file in sorted(screen_path.iterdir()):
        paths.append(file)
        hashes.append(_get_image_hash(file))
    return paths, hashes


def _get_image_hash(png_file: Path) -> str:
    return hashlib.sha256(_get_bytes_from_png(png_file)).hexdigest()


def _get_bytes_from_png(png_file: Path) -> bytes:
    """Decode a PNG file into bytes representing all the pixels.

    Is necessary because Linux and Mac are using different PNG encoding libraries,
    and we need the file hashes to be the same on both platforms.
    """
    return Image.open(str(png_file)).tobytes()


def _hash_files(path: Path) -> str:
    files = path.iterdir()
    hasher = hashlib.sha256()
    for file in sorted(files):
        hasher.update(_get_bytes_from_png(file))
    return hasher.digest().hex()


def get_last_call_test_result(request: pytest.FixtureRequest) -> bool | None:
    if not hasattr(request.node, "rep_call"):
        return None
    return request.node.rep_call.passed  # type: ignore


def _get_test_name(node_id: str) -> str:
    test_path, func_id = node_id.split("::", maxsplit=1)
    assert test_path.endswith(".py")

    _tests, *path_in_group = test_path.split("/")

    func_id = re.sub(r"::.*?::", "-", func_id)

    test_path_prefix = "-".join(path_in_group)
    new_name = f"{test_path_prefix}::{func_id}"
    new_name = new_name.replace("/", "-")

    if len(new_name) <= 100:
        return new_name

    differentiator = hashlib.sha256(new_name.encode()).hexdigest()
    shortened_name = new_name[:91] + "-" + differentiator[:8]
    return shortened_name


def get_screen_path(test_case: TestCase) -> Path | None:
    test_name = test_case.id
    path = SCREENS_DIR / test_name / "actual"
    if path.exists():
        return path
    path = SCREENS_DIR / test_name / "recorded"
    if path.exists():
        print(
            f"WARNING: no actual screens for {test_name}, recording may be outdated: {path}"
        )
        return path
    print(f"WARNING: missing screens for {test_name}. Did the test run?")
    return None


def screens_diff(
    expected_hashes: list[str], actual_hashes: list[str]
) -> t.Iterator[tuple[str | None, str | None]]:
    diff = SequenceMatcher(
        None, expected_hashes, actual_hashes, autojunk=False
    ).get_opcodes()
    for _tag, i1, i2, j1, j2 in diff:
        expected_slice = expected_hashes[i1:i2]
        actual_slice = actual_hashes[j1:j2]
        yield from zip_longest(expected_slice, actual_slice, fillvalue=None)


@dataclass(frozen=True)
class TestCase:
    model: str
    language: str
    name: str

    @classmethod
    def build(cls, client: Client, request: pytest.FixtureRequest) -> Self:
        name = _get_test_name(request.node.nodeid)
        full_language = client.features.language
        assert full_language
        language = full_language[:2]
        return cls(
            model=client.model.internal_name,
            name=name,
            language=language,
        )

    @staticmethod
    def get_language_from_fixture_name(fixture_name: str) -> str:
        m = _FIXTURE_KEY_RE.match(fixture_name)
        if m is None:
            raise ValueError(f"Invalid fixture key: {fixture_name}")
        return m.group("language")

    @property
    def id(self) -> str:
        return f"{self.model}_{self.language}-{self.name}"

    @property
    def fixtures_name(self) -> str:
        return self.id

    @classmethod
    def from_fixtures(cls, fixtures_name: str) -> Self:
        m = _FIXTURE_KEY_RE.match(fixtures_name)
        if m is None:
            raise ValueError(f"Invalid fixture key: {fixtures_name}")
        return cls(
            model=m.group("model"),
            language=m.group("language"),
            name=m.group("name"),
        )

    @property
    def dir(self) -> Path:
        return SCREENS_DIR / self.id

    @property
    def screen_text_file(self) -> Path:
        return self.dir / "screens.txt"

    @property
    def actual_dir(self) -> Path:
        return self.dir / "actual"

    @cached_property
    def actual_screens(self) -> tuple[list[Path], list[str]]:
        _rename_records(self.actual_dir)
        return screens_and_hashes(self.actual_dir)

    @property
    def recorded_dir(self) -> Path:
        return self.dir / "recorded"

    @cached_property
    def recorded_screens(self) -> tuple[list[Path], list[str]]:
        return screens_and_hashes(self.recorded_dir)

    def build_result(self, request: pytest.FixtureRequest) -> TestResult:
        _rename_records(self.actual_dir)
        result = TestResult(
            test=self,
            passed=get_last_call_test_result(request),
            actual_hash=_hash_files(self.actual_dir),
            images=self.actual_screens[1],
        )
        result.save_metadata()
        return result

    def replace(self, **kwargs) -> Self:
        return replace(self, **kwargs)


@dataclass
class TestResult:
    test: TestCase
    passed: bool | None
    actual_hash: str
    images: list[str]
    expected_hash: str | None = field(default=None)

    def __post_init__(self) -> None:
        if self.expected_hash is None:
            self.expected_hash = (
                get_current_fixtures()
                .get(self.test.model, {})
                .get(self.test.fixtures_name)
            )

    def save_metadata(self) -> None:
        metadata = asdict(self)
        (self.test.dir / "metadata.json").write_text(
            json.dumps(metadata, indent=2, sort_keys=True) + "\n"
        )

    @property
    def ui_passed(self) -> bool:
        return self.actual_hash == self.expected_hash

    @classmethod
    def load(cls, testdir: Path) -> Self:
        metadata = json.loads((testdir / "metadata.json").read_text())
        test = TestCase(
            model=metadata["test"]["model"],
            name=metadata["test"]["name"],
            language=metadata["test"]["language"],
        )
        return cls(
            test=test,
            passed=metadata["passed"],
            actual_hash=metadata["actual_hash"],
            expected_hash=metadata["expected_hash"],
            images=metadata["images"],
        )

    @classmethod
    def recent_results(cls) -> t.Iterator[Self]:
        for testdir in sorted(SCREENS_DIR.iterdir()):
            meta = testdir / "metadata.json"
            if not meta.exists():
                continue
            yield cls.load(testdir)

    @classmethod
    def recent_ui_failures(cls) -> t.Iterator[Self]:
        """Returning just the results that resulted in UI failure."""
        for result in cls.recent_results():
            if not result.ui_passed:
                yield result

    def store_recorded(self) -> None:
        self.expected_hash = self.actual_hash
        shutil.rmtree(self.test.recorded_dir, ignore_errors=True)
        shutil.copytree(
            self.test.actual_dir,
            self.test.recorded_dir,
            symlinks=True,
        )

    def diff_lines(self) -> t.Iterable[tuple[str | None, str | None]]:
        _, expected_hashes = self.test.recorded_screens
        if not expected_hashes:
            warnings.warn("No recorded screens found, is this a new test?")
        _, actual_hashes = self.test.actual_screens
        return screens_diff(expected_hashes, actual_hashes)
