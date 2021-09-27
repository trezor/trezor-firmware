import hashlib
import json
import re
import shutil
from contextlib import contextmanager
from pathlib import Path

import pytest
from _pytest.outcomes import Failed
from PIL import Image

from .reporting import testreport

UI_TESTS_DIR = Path(__file__).parent.resolve()
SCREENS_DIR = UI_TESTS_DIR / "screens"
HASH_FILE = UI_TESTS_DIR / "fixtures.json"
SUGGESTION_FILE = UI_TESTS_DIR / "fixtures.suggestion.json"
FILE_HASHES = {}
ACTUAL_HASHES = {}
PROCESSED = set()


def get_test_name(node_id):
    # Test item name is usually function name, but when parametrization is used,
    # parameters are also part of the name. Some functions have very long parameter
    # names (tx hashes etc) that run out of maximum allowable filename length, so
    # we limit the name to first 100 chars. This is not a problem with txhashes.
    new_name = node_id.replace("tests/device_tests/", "")
    # remove ::TestClass:: if present because it is usually the same as the test file name
    new_name = re.sub(r"::.*?::", "-", new_name)
    new_name = new_name.replace("/", "-")  # in case there is "/"
    if len(new_name) <= 100:
        return new_name
    return new_name[:91] + "-" + hashlib.sha256(new_name.encode()).hexdigest()[:8]


def _process_recorded(screen_path, test_name):
    # calculate hash
    FILE_HASHES[test_name] = _hash_files(screen_path)
    _rename_records(screen_path)
    PROCESSED.add(test_name)


def _rename_records(screen_path):
    # rename screenshots
    for index, record in enumerate(sorted(screen_path.iterdir())):
        record.replace(screen_path / f"{index:08}.png")


def _hash_files(path: Path) -> str:
    files = path.iterdir()
    hasher = hashlib.sha256()
    for file in sorted(files):
        hasher.update(_get_bytes_from_png(str(file)))

    return hasher.digest().hex()


def _get_bytes_from_png(png_file: str) -> bytes:
    """Decode a PNG file into bytes representing all the pixels.

    Is necessary because Linux and Mac are using different PNG encoding libraries,
    and we need the file hashes to be the same on both platforms.
    """
    return Image.open(png_file).tobytes()


def _process_tested(fixture_test_path, test_name):
    PROCESSED.add(test_name)

    actual_path = fixture_test_path / "actual"
    actual_hash = _hash_files(actual_path)
    ACTUAL_HASHES[test_name] = actual_hash

    _rename_records(actual_path)

    expected_hash = FILE_HASHES.get(test_name)
    if expected_hash is None:
        pytest.fail(f"Hash of {test_name} not found in fixtures.json")

    if actual_hash != expected_hash:
        file_path = testreport.failed(
            fixture_test_path, test_name, actual_hash, expected_hash
        )

        pytest.fail(
            f"Hash of {test_name} differs.\n"
            f"Expected:  {expected_hash}\n"
            f"Actual:    {actual_hash}\n"
            f"Diff file: {file_path}"
        )
    else:
        testreport.passed(fixture_test_path, test_name, actual_hash)


@contextmanager
def screen_recording(client, request):
    test_ui = request.config.getoption("ui")
    test_name = get_test_name(request.node.nodeid)
    screens_test_path = SCREENS_DIR / test_name

    if test_ui == "record":
        screen_path = screens_test_path / "recorded"
    else:
        screen_path = screens_test_path / "actual"

    if not screens_test_path.exists():
        screens_test_path.mkdir()
    # remove previous files
    shutil.rmtree(screen_path, ignore_errors=True)
    screen_path.mkdir()

    try:
        client.debug.start_recording(str(screen_path))
        yield
    finally:
        # Wait for response to Initialize, which gives the emulator time to catch up
        # and redraw the homescreen. Otherwise there's a race condition between that
        # and stopping recording.
        client.init_device()
        client.debug.stop_recording()

    if test_ui == "record":
        _process_recorded(screen_path, test_name)
    else:
        _process_tested(screens_test_path, test_name)


def list_missing():
    return set(FILE_HASHES.keys()) - PROCESSED


def read_fixtures():
    if not HASH_FILE.exists():
        raise ValueError("File fixtures.json not found.")
    global FILE_HASHES
    FILE_HASHES = json.loads(HASH_FILE.read_text())


def write_fixtures(remove_missing: bool):
    HASH_FILE.write_text(_get_fixtures_content(FILE_HASHES, remove_missing))


def write_fixtures_suggestion(remove_missing: bool):
    SUGGESTION_FILE.write_text(_get_fixtures_content(ACTUAL_HASHES, remove_missing))


def _get_fixtures_content(fixtures: dict, remove_missing: bool):
    if remove_missing:
        fixtures = {i: fixtures[i] for i in PROCESSED}
    else:
        fixtures = fixtures

    return json.dumps(fixtures, indent="", sort_keys=True) + "\n"


def main():
    read_fixtures()
    for record in SCREENS_DIR.iterdir():
        if not (record / "actual").exists():
            continue

        try:
            _process_tested(record, record.name)
            print("PASSED:", record.name)
        except Failed:
            print("FAILED:", record.name)

    testreport.index()
