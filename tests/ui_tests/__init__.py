import hashlib
import json
import re
import shutil
from contextlib import contextmanager
from pathlib import Path

import pytest

from .reporting import testreport

UI_TESTS_DIR = Path(__file__).parent.resolve()
HASH_FILE = UI_TESTS_DIR / "fixtures.json"
HASHES = {}
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
    return new_name[:100]


def _process_recorded(screen_path, test_name):
    # calculate hash
    HASHES[test_name] = _hash_files(screen_path)
    _rename_records(screen_path)
    PROCESSED.add(test_name)


def _rename_records(screen_path):
    # rename screenshots
    for index, record in enumerate(sorted(screen_path.iterdir())):
        record.replace(screen_path / f"{index:08}.png")


def _hash_files(path):
    files = path.iterdir()
    hasher = hashlib.sha256()
    for file in sorted(files):
        hasher.update(file.read_bytes())

    return hasher.digest().hex()


def _process_tested(fixture_test_path, test_name):
    expected_hash = HASHES.get(test_name)
    if expected_hash is None:
        raise ValueError("Hash for '%s' not found in fixtures.json" % test_name)
    PROCESSED.add(test_name)

    actual_path = fixture_test_path / "actual"
    actual_hash = _hash_files(actual_path)

    _rename_records(actual_path)

    if actual_hash != expected_hash:
        file_path = testreport.failed(
            fixture_test_path, test_name, actual_hash, expected_hash
        )

        pytest.fail(
            "Hash of {} differs.\nExpected:  {}\nActual:    {}\nDiff file: {}".format(
                test_name, expected_hash, actual_hash, file_path
            )
        )
    else:
        testreport.passed(fixture_test_path, test_name, actual_hash)


@contextmanager
def screen_recording(client, request):
    test_ui = request.config.getoption("ui")
    test_name = get_test_name(request.node.nodeid)
    screens_test_path = UI_TESTS_DIR / "screens" / test_name

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
        if test_ui == "record":
            _process_recorded(screen_path, test_name)
        else:
            _process_tested(screens_test_path, test_name)
    finally:
        client.debug.stop_recording()


def list_missing():
    return set(HASHES.keys()) - PROCESSED


def read_fixtures():
    if not HASH_FILE.exists():
        raise ValueError("File fixtures.json not found.")
    global HASHES
    HASHES = json.loads(HASH_FILE.read_text())


def write_fixtures(remove_missing: bool):
    if remove_missing:
        write = {i: HASHES[i] for i in PROCESSED}
    else:
        write = HASHES

    HASH_FILE.write_text(json.dumps(write, indent="", sort_keys=True) + "\n")
