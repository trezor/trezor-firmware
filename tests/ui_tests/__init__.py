import hashlib
import re
import shutil
from contextlib import contextmanager
from pathlib import Path

import pytest

from . import report

UI_TESTS_DIR = Path(__file__).parent.resolve()


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


def _check_fixture_directory(fixture_dir, screen_path):
    # create the fixture dir if it does not exist
    if not fixture_dir.exists():
        fixture_dir.mkdir()

    # delete old files
    shutil.rmtree(screen_path, ignore_errors=True)
    screen_path.mkdir()


def _process_recorded(screen_path):
    # create hash
    digest = _hash_files(screen_path)

    (screen_path.parent / "hash.txt").write_text(digest)
    _rename_records(screen_path)


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
    hash_file = fixture_test_path / "hash.txt"

    if not hash_file.exists():
        raise ValueError("File hash.txt not found.")

    expected_hash = hash_file.read_text()
    actual_path = fixture_test_path / "actual"
    actual_hash = _hash_files(actual_path)

    _rename_records(actual_path)

    if actual_hash != expected_hash:
        file_path = report.failed(
            fixture_test_path, test_name, actual_hash, expected_hash
        )

        pytest.fail(
            "Hash of {} differs.\nExpected:  {}\nActual:    {}\nDiff file: {}".format(
                test_name, expected_hash, actual_hash, file_path
            )
        )
    else:
        report.passed(fixture_test_path, test_name, actual_hash)


@contextmanager
def screen_recording(client, request):
    test_ui = request.config.getoption("ui")
    test_name = get_test_name(request.node.nodeid)
    fixture_test_path = UI_TESTS_DIR / "fixtures" / test_name

    if test_ui == "record":
        screen_path = fixture_test_path / "recorded"
    elif test_ui == "test":
        screen_path = fixture_test_path / "actual"
    else:
        raise ValueError("Invalid 'ui' option.")

    # remove previous files
    shutil.rmtree(screen_path, ignore_errors=True)
    screen_path.mkdir()

    try:
        client.debug.start_recording(str(screen_path))
        yield
    finally:
        client.debug.stop_recording()
        if test_ui == "record":
            _process_recorded(screen_path)
        elif test_ui == "test":
            _process_tested(fixture_test_path, test_name)
        else:
            raise ValueError("Invalid 'ui' option.")
