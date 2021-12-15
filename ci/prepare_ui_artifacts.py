import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).parent / ".."
sys.path.insert(0, str(ROOT))
# Needed for setup purposes, filling the FILE_HASHES dict
from tests.ui_tests import read_fixtures  # isort:skip

read_fixtures()
from tests.ui_tests import _hash_files, FILE_HASHES, SCREENS_DIR  # isort:skip


for test_case in FILE_HASHES.keys():
    recorded_dir = SCREENS_DIR / test_case / "recorded"
    expected_hash = FILE_HASHES[test_case]
    actual_hash = _hash_files(recorded_dir)
    assert expected_hash == actual_hash
    shutil.make_archive(ROOT / "ci/ui_test_records" / actual_hash, "zip", recorded_dir)
