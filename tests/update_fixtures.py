#!/usr/bin/env python3

from ui_tests import update_fixtures_with_diff

changes_amount = update_fixtures_with_diff()

print(f"{changes_amount} hashes updated in fixtures.json file.")
