import hashlib
import re
import shutil
from contextlib import contextmanager
from distutils.dir_util import copy_tree
from pathlib import Path

import pytest

from . import html


def _get_test_dirname(node):
    # This composes the dirname from the test module name and test item name.
    # Test item name is usually function name, but when parametrization is used,
    # parameters are also part of the name. Some functions have very long parameter
    # names (tx hashes etc) that run out of maximum allowable filename length, so
    # we limit the name to first 100 chars. This is not a problem with txhashes.
    node_name = re.sub(r"\W+", "_", node.name)[:100]
    node_module_name = node.getparent(pytest.Module).name
    return f"{node_module_name}_{node_name}"


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
        diff_file = html.diff_file(
            fixture_test_path, test_name, actual_hash, expected_hash
        )

        pytest.fail(
            "Hash of {} differs.\nExpected:  {}\nActual:    {}\nDiff file: {}".format(
                test_name, expected_hash, actual_hash, diff_file
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
    test_ui = request.config.getoption("ui")
    test_name = _get_test_dirname(request.node)
    fixture_test_path = Path(__file__).parent.resolve() / "fixtures" / test_name

    if test_ui == "record":
        screen_path = fixture_test_path / "recorded"
    elif test_ui == "test":
        screen_path = fixture_test_path / "actual"
    else:
        raise ValueError("Invalid 'ui' option.")

    _check_fixture_directory(fixture_test_path, screen_path)

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
