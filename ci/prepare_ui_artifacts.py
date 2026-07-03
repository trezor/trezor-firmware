import shutil
import sys
from multiprocessing import Pool
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from tests.ui_tests.common import TestResult, get_current_fixtures  # isort:skip

FIXTURES = get_current_fixtures()


def compute_hash(result: TestResult) -> TestResult | None:
    if not result.passed or result.expected_hash != result.actual_hash:
        print("WARNING: skipping failed test", result.test.id)
        return None

    actual_hash = result.actual_hash
    expected_hash = (
        FIXTURES.get(result.test.model, {})
        .get(result.test.group, {})
        .get(result.test.fixtures_name)
    )
    assert result.expected_hash == actual_hash
    assert expected_hash == actual_hash
    return result


def create_zip(item: tuple[str, TestResult]) -> None:
    archive_path, result = item
    shutil.make_archive(archive_path, "zip", result.test.actual_dir)


def main():
    with Pool() as pool:
        all_results = list(TestResult.recent_results())
        print(f"Hashing {len(all_results)} results")
        # deduplicate results by `actual_hash`, and skip failed tests
        results_map = {
            str(ROOT / "ci/ui_test_records" / result.actual_hash): result
            for result in pool.imap_unordered(compute_hash, all_results)
            if result is not None
        }
        print(f"Creating {len(results_map)} ZIP files")
        for _ in pool.imap_unordered(create_zip, results_map.items()):
            pass


if __name__ == "__main__":
    main()
