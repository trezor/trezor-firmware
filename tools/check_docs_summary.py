"""
This script lists names of markdown files (.md extenstion) present in docs/ directory
which are not referenced in SUMMARY.md file which serves as a firmware docu mainpage.

Running the script:
- `python tools/check_docs_summary.py` from trezor-firmware root directory.
"""

import re
import sys
from pathlib import Path
from typing import Generator, Iterable, Set

DOCS_DIR = "docs/"
SUMMARY_FILENAME = "SUMMARY.md"
RE_MARKDOWN_LINK = r"\[.*?\]\((.+.md)\)"


def gen_pat_in_file(
    filepath: str, pat: re.Pattern, grp_idx: int
) -> Generator[str, None, None]:
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f.readlines():
            match = re.search(pat, line)
            if match:
                yield match.group(grp_idx)


def gen_convert_to_str(inputs: Iterable[Path]) -> Generator[str, None, None]:
    for i in inputs:
        yield str(i)


def gen_ltrim_pat(inputs: Iterable[str], pat: str) -> Generator[str, None, None]:
    for i in inputs:
        if i.startswith(pat):
            yield i[len(pat) :]


def gen_skip(inputs: Iterable[str], what: str) -> Generator[str, None, None]:
    for i in inputs:
        if i != what:
            yield i


def difference(g1: Iterable[str], g2: Iterable[str]) -> Generator[str, None, None]:
    set_g2: Set[str] = set(g2)
    for item in g1:
        if item not in set_g2:
            yield item


def print_result(filenames: Iterable[str]) -> None:
    if not filenames:
        print("OK")
        sys.exit(0)
    else:
        print(
            f"ERROR: these files exist in {DOCS_DIR} but are not linked in {DOCS_DIR + SUMMARY_FILENAME}"
        )
        for f in filenames:
            print(f"\t- {f}")
        sys.exit(1)


def main():
    re_md_link = re.compile(RE_MARKDOWN_LINK)

    md_files_in_docs_dir = Path(DOCS_DIR).rglob("*.md")
    md_files_in_docs_dir = gen_convert_to_str(md_files_in_docs_dir)
    md_files_in_docs_dir = gen_ltrim_pat(md_files_in_docs_dir, DOCS_DIR)
    md_files_in_docs_dir = gen_skip(md_files_in_docs_dir, SUMMARY_FILENAME)

    md_files_linked_in_summary = gen_pat_in_file(
        DOCS_DIR + SUMMARY_FILENAME, re_md_link, 1
    )
    diff = difference(md_files_in_docs_dir, md_files_linked_in_summary)
    print_result(list(diff))


if __name__ == "__main__":
    main()
