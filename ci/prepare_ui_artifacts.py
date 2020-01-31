import hashlib
import json
import shutil
from pathlib import Path


def _hash_files(path):
    files = path.iterdir()
    hasher = hashlib.sha256()
    for file in sorted(files):
        hasher.update(file.read_bytes())

    return hasher.digest().hex()


root = Path().cwd() / "../tests/ui_tests"
screens = root / "screens"
fixtures = root / "fixtures.json"

hashes = json.loads(fixtures.read_text())

for test_case in hashes.keys():
    recorded_dir = screens / test_case / "recorded"
    expected_hash = hashes[test_case]
    actual_hash = _hash_files(recorded_dir)
    assert expected_hash == actual_hash
    shutil.make_archive("ui_test_records/" + actual_hash, "zip", recorded_dir)
