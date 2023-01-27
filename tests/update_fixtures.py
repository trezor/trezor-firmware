#!/usr/bin/env python3
import click

from ui_tests import update_fixtures


@click.command()
@click.option("-r", "--remove-missing", is_flag=True, help="Remove missing tests")
def main(remove_missing: bool) -> None:
    """Update fixtures file with results from latest test run."""
    changes_amount = update_fixtures(remove_missing)
    print(f"Updated fixtures.json with data from {changes_amount} tests.")


if __name__ == "__main__":
    main()
