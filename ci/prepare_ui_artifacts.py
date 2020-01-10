import hashlib
import shutil
from pathlib import Path


def _hash_files(path):
    files = path.iterdir()
    hasher = hashlib.sha256()
    for file in sorted(files):
        hasher.update(file.read_bytes())

    return hasher.digest().hex()


fixture_root = Path().cwd() / "../tests/ui_tests/fixtures/"

for recorded_dir in fixture_root.glob("*/recorded"):
    expected_hash = (recorded_dir.parent / "hash.txt").read_text()
    actual_hash = _hash_files(recorded_dir)
    assert expected_hash == actual_hash
    shutil.make_archive("ui_test_records/" + actual_hash, "zip", recorded_dir)
