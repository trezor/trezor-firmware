import hashlib
import shutil
from pathlib import Path


def _hash_files(files):
    hasher = hashlib.sha256()
    for file in sorted(files):
        with open(file, "rb") as f:
            content = f.read()
            hasher.update(content)

    return hasher.digest().hex()


def _compare_hash(test_dir, hash):
    with open(test_dir / "hash.txt", "r") as f:
        content = f.read()
        assert hash == content


fixture_root = Path().cwd() / "../tests/ui_tests/fixtures"

for test_dir in fixture_root.iterdir():
    if test_dir.is_dir():
        recorded_dir = test_dir / "recorded"
        if recorded_dir.exists():
            hash = _hash_files(recorded_dir.iterdir())
            _compare_hash(test_dir, hash)
            shutil.make_archive("tmp/" + hash, "zip", recorded_dir)
