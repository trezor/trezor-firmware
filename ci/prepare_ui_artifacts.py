import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
# Needed for setup purposes, filling the FILE_HASHES dict
from tests.ui_tests.common import TestResult, _hash_files  # isort:skip
from tests.ui_tests.common import get_current_fixtures  # isort:skip


FIXTURES = get_current_fixtures()

for result in TestResult.recent_results():
    if not result.passed or result.expected_hash != result.actual_hash:
        print("WARNING: skipping failed test", result.test.id)
        continue

    actual_hash = _hash_files(result.test.actual_dir)
    expected_hash = (
        FIXTURES.get(result.test.model, {})
        .get(result.test.group, {})
        .get(result.test.fixtures_name)
    )
    assert result.expected_hash == actual_hash
    assert expected_hash == actual_hash
    shutil.make_archive(
        str(ROOT / "ci/ui_test_records" / actual_hash), "zip", result.test.actual_dir
    )
