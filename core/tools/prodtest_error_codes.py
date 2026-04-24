#!/usr/bin/env python3
"""
Parse prodtest_error_codes.h and emit a JSON error code table.

The JSON is intended for host-side tooling that needs to map numeric error
codes received over the prodtest CLI back to human-readable names and modules.

Usage:
    prodtest_error_codes.py                        # write to the default path
    prodtest_error_codes.py -o errors.json         # write to a different file
    prodtest_error_codes.py --stdout               # print JSON to stdout
    prodtest_error_codes.py --check                # verify the file is up to date
    prodtest_error_codes.py --header path/to/prodtest_error_codes.h
"""

import argparse
import json
import re
import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).parent
CORE_DIR = TOOLS_DIR.parent

DEFAULT_HEADER = CORE_DIR / "embed/projects/prodtest/prodtest_error_codes.h"
DEFAULT_CLI_HEADER = CORE_DIR / "embed/rtl/inc/rtl/cli.h"
DEFAULT_VERSION_HEADER = CORE_DIR / "embed/projects/prodtest/version.h"
DEFAULT_OUTPUT = CORE_DIR / "embed/projects/prodtest/error_codes.json"

# Matches:  // === backup-ram (1000–1999) ===
# or:       // === otp — some note (10000–10999) ===
_MODULE_RE = re.compile(r"//\s*===\s*(.+?)\s*\((\d+)\s*[–-]\s*(\d+)\)\s*")

# Matches:  PRODTEST_ERR_FOO_BAR = 1234,
_ENUM_RE = re.compile(r"^\s*(PRODTEST_ERR_\w+)\s*=\s*(\d+)\s*,?")

# Matches:  #define CLI_ERROR_INVALID_CMD 1
_CLI_DEFINE_RE = re.compile(r"^\s*#define\s+(CLI_ERROR_\w+)\s+(\d+)")

# Matches:  #define VERSION_MAJOR 0
_VERSION_DEFINE_RE = re.compile(
    r"^\s*#define\s+(VERSION_MAJOR|VERSION_MINOR|VERSION_PATCH|VERSION_BUILD)\s+(\d+)"
)


def parse_prodtest_header(path: Path) -> tuple[list[dict], list[dict]]:
    """Return (modules, errors) parsed from prodtest_error_codes.h."""
    modules: list[dict] = []
    errors: list[dict] = []
    current_module: str | None = None

    for line in path.read_text(encoding="utf-8").splitlines():
        m = _MODULE_RE.search(line)
        if m:
            # Extract the module name, stripping any trailing note after " — "
            raw_name = m.group(1).strip()
            name = raw_name.split(" — ")[0].strip()
            range_start = int(m.group(2))
            range_end = int(m.group(3))
            current_module = name
            modules.append(
                {"module": name, "range_start": range_start, "range_end": range_end}
            )
            continue

        m = _ENUM_RE.match(line)
        if m:
            errors.append(
                {
                    "code": int(m.group(2)),
                    "name": m.group(1),
                    "module": current_module,
                }
            )

    return modules, errors


def parse_cli_header(path: Path) -> list[dict]:
    """Return framework-level error codes from cli.h."""
    codes = []
    for line in path.read_text(encoding="utf-8").splitlines():
        m = _CLI_DEFINE_RE.match(line)
        if m:
            codes.append({"code": int(m.group(2)), "name": m.group(1)})
    return sorted(codes, key=lambda c: c["code"])


def parse_version_header(path: Path) -> str:
    """Return the prodtest version string from version.h as 'MAJOR.MINOR.PATCH.BUILD'."""
    parts: dict[str, int] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        m = _VERSION_DEFINE_RE.match(line)
        if m:
            parts[m.group(1)] = int(m.group(2))
    missing = [
        k
        for k in ("VERSION_MAJOR", "VERSION_MINOR", "VERSION_PATCH", "VERSION_BUILD")
        if k not in parts
    ]
    if missing:
        raise ValueError(f"{path}: missing {', '.join(missing)}")
    return (
        f"{parts['VERSION_MAJOR']}.{parts['VERSION_MINOR']}."
        f"{parts['VERSION_PATCH']}.{parts['VERSION_BUILD']}"
    )


def build_output(
    modules: list[dict],
    errors: list[dict],
    framework_codes: list[dict],
    header_path: Path,
    version: str,
) -> dict:
    return {
        "source": header_path.name,
        "prodtest_version": version,
        "framework_codes": framework_codes,
        "modules": modules,
        "errors": errors,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--header",
        type=Path,
        default=DEFAULT_HEADER,
        help=f"Path to prodtest_error_codes.h (default: {DEFAULT_HEADER})",
    )
    parser.add_argument(
        "--cli-header",
        type=Path,
        default=DEFAULT_CLI_HEADER,
        help=f"Path to cli.h for framework codes (default: {DEFAULT_CLI_HEADER})",
    )
    parser.add_argument(
        "--version-header",
        type=Path,
        default=DEFAULT_VERSION_HEADER,
        help=f"Path to prodtest version.h (default: {DEFAULT_VERSION_HEADER})",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output file path (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Print JSON to stdout instead of writing to a file",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit non-zero if the output file is missing or out of date",
    )
    parser.add_argument(
        "--indent",
        type=int,
        default=2,
        help="JSON indentation (default: 2)",
    )
    args = parser.parse_args()

    if not args.header.exists():
        print(f"error: header not found: {args.header}", file=sys.stderr)
        sys.exit(1)

    modules, errors = parse_prodtest_header(args.header)

    framework_codes: list[dict] = []
    if args.cli_header.exists():
        framework_codes = parse_cli_header(args.cli_header)

    if not args.version_header.exists():
        print(
            f"error: version header not found: {args.version_header}", file=sys.stderr
        )
        sys.exit(1)
    version = parse_version_header(args.version_header)

    result = build_output(modules, errors, framework_codes, args.header, version)
    json_str = json.dumps(result, indent=args.indent) + "\n"

    if args.check:
        if not args.output.exists():
            print(f"error: {args.output} does not exist", file=sys.stderr)
            sys.exit(1)
        current = args.output.read_text(encoding="utf-8")
        if current != json_str:
            print(
                f"error: {args.output} is out of date — re-run"
                f" {Path(__file__).name} to regenerate",
                file=sys.stderr,
            )
            sys.exit(1)
        return

    if args.stdout:
        sys.stdout.write(json_str)
    else:
        args.output.write_text(json_str, encoding="utf-8")
        print(
            f"wrote {len(errors)} error codes across {len(modules)} modules"
            f" to {args.output}",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
