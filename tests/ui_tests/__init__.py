import hashlib
import re
import shutil
from contextlib import contextmanager
from distutils.dir_util import copy_tree
from pathlib import Path

import pytest

from .html import create_diff_doc


def _get_test_dirname(node):
    # This composes the dirname from the test module name and test item name.
    # Test item name is usually function name, but when parametrization is used,
    # parameters are also part of the name. Some functions have very long parameter
    # names (tx hashes etc) that run out of maximum allowable filename length, so
    # we limit the name to first 100 chars. This is not a problem with txhashes.
    node_name = re.sub(r"\W+", "_", node.name)[:100]
    node_module_name = node.getparent(pytest.Module).name
    return "{}_{}".format(node_module_name, node_name)


def _check_fixture_directory(fixture_dir, screen_path):
    # create the fixture dir if it does not exist
    if not fixture_dir.exists():
        fixture_dir.mkdir()

    # delete old files
    shutil.rmtree(screen_path, ignore_errors=True)
    screen_path.mkdir()


def _process_recorded(screen_path):
    records = sorted(screen_path.iterdir())

    # create hash
    digest = _hash_files(records)
    with open(screen_path / "../hash.txt", "w") as f:
        f.write(digest)
    _rename_records(screen_path)


def _rename_records(screen_path):
    # rename screenshots
    for index, record in enumerate(sorted(screen_path.iterdir())):
        filename = screen_path / "{:08}.png".format(index)
        record.replace(filename)


def _hash_files(files):
    hasher = hashlib.sha256()
    for file in sorted(files):
        with open(file, "rb") as f:
            content = f.read()
            hasher.update(content)

    return hasher.digest().hex()


def _process_tested(fixture_test_path, test_name):
    hash_file = fixture_test_path / "hash.txt"

    if not hash_file.exists():
        raise ValueError("File hash.txt not found.")

    with open(hash_file, "r") as f:
        expected_hash = f.read()

    actual_path = fixture_test_path / "actual"
    _rename_records(actual_path)

    records = sorted(actual_path.iterdir())
    actual_hash = _hash_files(records)

    if actual_hash != expected_hash:
        create_diff_doc(fixture_test_path, test_name, actual_hash, expected_hash)
        pytest.fail(
            "Hash of {} differs.\nExpected: {}\nActual:   {}".format(
                test_name, expected_hash, actual_hash
            )
        )
    else:
        copy_tree(
            str(fixture_test_path / "actual"), str(fixture_test_path / "recorded")
        )
        if (fixture_test_path / "diff.html").exists():
            (fixture_test_path / "diff.html").unlink()


@contextmanager
def screen_recording(client, request):
    if not request.node.get_closest_marker("skip_ui"):
        test_screen = request.config.getoption("test_screen")
    else:
        test_screen = ""

    if not test_screen:
        yield
        return

    fixture_root = Path(__file__) / "../fixtures"
    test_name = _get_test_dirname(request.node)
    fixture_test_path = fixture_root.resolve() / test_name

    if test_screen == "record":
        screen_path = fixture_test_path / "recorded"
    elif test_screen == "test":
        screen_path = fixture_test_path / "actual"
    else:
        raise ValueError("Invalid test_screen option.")

    _check_fixture_directory(fixture_test_path, screen_path)

    try:
        client.debug.start_recording(str(screen_path))
        yield
    finally:
        client.debug.stop_recording()
        if test_screen == "record":
            _process_recorded(screen_path)
        elif test_screen == "test":
            _process_tested(fixture_test_path, test_name)
        else:
            raise ValueError("Invalid test_screen option.")
