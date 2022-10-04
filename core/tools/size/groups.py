#!/usr/bin/env python3
"""
Grouping symbols in binary into coherent categories.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Callable

from binsize import BinarySize, DataRow, StatisticsPlugin, set_root_dir

HERE = Path(__file__).resolve().parent
CORE_DIR = HERE.parent.parent

if len(sys.argv) > 1:
    BIN_TO_ANALYZE = sys.argv[1]
else:
    BIN_TO_ANALYZE = CORE_DIR / "build/firmware/firmware.elf"  # type: ignore
FILE_TO_SAVE = HERE / "size_binary_firmware_elf_results.txt"


def _categories_func(row: DataRow) -> str | None:
    # Defined inside the function so it can be seen in the function definition
    # (which is optionally printed)
    CATEGORIES: dict[str, Callable[[DataRow], bool]] = {
        "UI": lambda row: (
            row.source_definition.startswith(
                ("src/trezor/ui/", "embed/extmod/modtrezorui/")
            )
        ),
        "Crypto": lambda row: (
            row.source_definition.startswith(
                (
                    "vendor/trezor-crypto/",
                    "src/trezor/crypto/",
                    "embed/extmod/modtrezorcrypto/",
                )
            )
        ),
        "Secp256": lambda row: (
            row.source_definition.startswith("vendor/secp256k1-zkp/")
        ),
        "Storage": lambda row: (
            row.source_definition.startswith(("src/storage/", "vendor/trezor-storage/"))
        ),
        "Micropython": lambda row: row.source_definition.startswith(
            "vendor/micropython/"
        ),
        "Bitcoin app": lambda row: row.source_definition.startswith(
            "src/apps/bitcoin/"
        ),
        "Ethereum app": lambda row: row.source_definition.startswith(
            "src/apps/ethereum/"
        ),
        "Monero app": lambda row: row.source_definition.startswith("src/apps/monero/"),
        "Cardano app": lambda row: row.source_definition.startswith(
            "src/apps/cardano/"
        ),
        "Management app": lambda row: row.source_definition.startswith(
            "src/apps/management/"
        ),
        "Common apps": lambda row: row.source_definition.startswith("src/apps/common/"),
        "Webauthn app": lambda row: row.source_definition.startswith(
            "src/apps/webauthn/"
        ),
        "Altcoin apps": lambda row: (
            row.source_definition.startswith(
                (
                    "src/apps/nem/",
                    "src/apps/stellar/",
                    "src/apps/eos/",
                    "src/apps/tezos/",
                    "src/apps/ripple/",
                    "src/apps/zcash/",
                    "src/apps/binance/",
                )
            )
        ),
        "Other apps": lambda row: row.source_definition.startswith("src/apps/"),
        "Rest of src/": lambda row: row.source_definition.startswith("src/"),
        "Fonts": lambda row: row.source_definition.startswith("embed/lib/fonts/"),
        "Embed firmware": lambda row: row.source_definition.startswith(
            "embed/firmware/"
        ),
        "Trezorhal": lambda row: row.source_definition.startswith("embed/trezorhal/"),
        "Trezorio": lambda row: row.source_definition.startswith(
            "embed/extmod/modtrezorio/"
        ),
        "Trezorconfig": lambda row: row.source_definition.startswith(
            "embed/extmod/modtrezorconfig/"
        ),
        "Trezorutils": lambda row: row.source_definition.startswith(
            "embed/extmod/modtrezorutils/"
        ),
        "Embed extmod": lambda row: row.source_definition.startswith("embed/extmod/"),
        "Embed lib": lambda row: row.source_definition.startswith("embed/lib/"),
        "Rust": lambda row: (
            row.language == "Rust"
            or row.source_definition.startswith(("embed/rust/", "/cargo/registry"))
            or row.symbol_name.startswith(("trezor_tjpgdec", "qrcodegen"))
            or ".cargo/registry" in row.symbol_name
        ),
        "Frozen modules": lambda row: row.symbol_name.startswith("frozen_module"),
        ".bootloader": lambda row: row.symbol_name == ".bootloader",
        ".rodata + qstr + misc": lambda row: (
            row.symbol_name.startswith(
                (".rodata", "mp_qstr", "str1", "*fill*", ".text", "OUTLINED_FUNCTION")
            )
            or _has_32_hex(row.symbol_name)
        ),
    }

    for category, func in CATEGORIES.items():
        if func(row):
            return category
    return None


def _has_32_hex(text: str) -> bool:
    if "." in text:
        text = text.split(".")[0]
    return len(text) == 32 and all(c in "0123456789abcdef" for c in text)


def show_categories_statistics(
    STATS: StatisticsPlugin, include_categories_func: bool = False
) -> None:
    STATS.show(include_none=True, include_categories_func=include_categories_func)


def show_data_with_categories(
    STATS: StatisticsPlugin, file_to_save: str | Path | None = None
) -> None:
    STATS.show_data_with_categories(file_to_save, include_none=True)


def show_only_one_category(
    BS: BinarySize, category: str | None, file_to_save: str | Path | None = None
) -> None:
    BS.filter(lambda row: _categories_func(row) == category).show(
        file_to_save, debug=True
    )


def show_raw_bloaty_data() -> None:
    BinarySize().load_file(BIN_TO_ANALYZE, sections=(".flash", ".flash2")).show(
        HERE / "size_binary_firmware_elf_results_no_aggregation.txt"
    )


if __name__ == "__main__":
    set_root_dir(str(CORE_DIR))

    BS = (
        BinarySize()
        .load_file(BIN_TO_ANALYZE, sections=(".flash", ".flash2"))
        .use_map_file(
            CORE_DIR / "build/firmware/firmware.map", sections=(".flash", ".flash2")
        )
        .add_basic_info()
        .aggregate()
        .sort()
        .add_definitions()
    )
    STATS = StatisticsPlugin(BS, _categories_func)

    show_categories_statistics(STATS, include_categories_func=True)
    show_data_with_categories(STATS, FILE_TO_SAVE)
    show_only_one_category(BS, None, HERE / "size_binary_firmware_elf_results_None.txt")
