#!/usr/bin/env python3
"""Generate a model-specific .coveragerc file.

Imports the emulator model config from site_scons to determine which USE_*
flags are True/False for a given model, then writes a .coveragerc that
excludes code guarded by flags that are structurally unreachable.

Usage:
    ./tools/generate_coveragerc.py T3B1  # creates .coveragerc.T3B1
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CORE = HERE.parent

# Add site_scons to the import path so we can import model configs
sys.path.insert(0, str(CORE / "site_scons"))

import models  # noqa: E402  # type: ignore [Import "models" could not be resolved]

from trezorlib.debuglink import LayoutType  # noqa: E402
from trezorlib.models import CORE_MODELS, by_internal_name  # noqa: E402

# Features wanted for a typical CI emulator test build
FEATURES_WANTED = [
    "applet",
    "ble",
    "display",
    "dma2d",
    "input",
    "ipc",
    "kernel_mode",
    "optiga",
    "powerctl",
    "rgb_led",
    "sd_card",
    "secure_mode",
    "serial_number",
    "storage",
    "telemetry",
    "tropic",
    "usb",
    "usb_iface_wire",
    "usb_iface_debug",
    "usb_iface_webauthn",
    "dbg_console",
]

# feature name in features_available -> Python USE_* flag name
FEATURE_TO_FLAG: dict[str, str] = {
    "backlight": "USE_BACKLIGHT",
    "ble": "USE_BLE",
    "button": "USE_BUTTON",
    "optiga": "USE_OPTIGA",
    "power_manager": "USE_POWER_MANAGER",
    "sd_card": "USE_SD_CARD",
    "touch": "USE_TOUCH",
    "tropic": "USE_TROPIC",
    "telemetry": "USE_TELEMETRY",
    "serial_number": "USE_SERIAL_NUMBER",
    "rgb_led": "USE_RGB_LED",
    "n4w1": "USE_N4W1",
    "app_loading": "USE_APP_LOADING",
    "dbg_console": "USE_DBG_CONSOLE",
}

# Flags that are always False in emulator builds
ALWAYS_FALSE_IN_EMULATOR: list[str] = [
    "USE_HAPTIC",
    "USE_NRF",
]

# Base exclusion patterns (same as the default .coveragerc)
BASE_EXCLUDE_LINES = [
    "from typing import",
    "if TYPE_CHECKING:",
    r"^_.*const\(\d+",
    "assert False",
    "pass",
    "raise RuntimeError",
    "raise NotImplementedError",
    "def mem_dump",
    r"def __repr__(self)",
]


def get_features_available(model: str) -> list[str]:
    """Get the list of available features for a model's emulator build."""
    defines: list[str | tuple[str, str]] = []
    sources: list[str] = []
    paths: list[str] = []
    return models.configure_board(
        model, "emulator", FEATURES_WANTED, {}, defines, sources, paths
    )


def get_flag_values(model: str) -> dict[str, bool]:
    """Determine the value of each USE_* flag for a model's emulator."""
    features = get_features_available(model)

    flags: dict[str, bool] = {}

    for feature, flag in FEATURE_TO_FLAG.items():
        flags[flag] = feature in features

    for flag in ALWAYS_FALSE_IN_EMULATOR:
        flags[flag] = False

    return flags


def generate_coveragerc(model: str, flags: dict[str, bool]) -> str:
    """Generate .coveragerc content with model-specific exclusions."""
    lines = [
        "[report]",
        "# Regexes for lines to exclude from consideration",
        "exclude_lines =",
    ]

    for pattern in BASE_EXCLUDE_LINES:
        lines.append(f"    {pattern}")

    false_flags = sorted(f for f, v in flags.items() if not v)
    true_flags = sorted(f for f, v in flags.items() if v)

    if false_flags or true_flags:
        lines.append("    # model-specific: exclude unreachable USE_* branches")

    for flag in false_flags:
        lines.append(rf"    if utils\.{flag}")
        lines.append(rf"    elif utils\.{flag}")

    for flag in true_flags:
        lines.append(rf"    if not utils\.{flag}")
        lines.append(rf"    elif not utils\.{flag}")

    # UI_LAYOUT exclusions: each model has exactly one layout
    this_layout = LayoutType.from_internal_name(model)
    other_layouts = [la for la in LayoutType if la not in (this_layout, LayoutType.T1)]
    if other_layouts:
        lines.append("    # model-specific: exclude unreachable UI_LAYOUT branches")
    for la in other_layouts:
        name = la.name.upper()
        lines.append(rf'    if utils\.UI_LAYOUT == "{name}"')
        lines.append(rf'    elif utils\.UI_LAYOUT == "{name}"')

    # INTERNAL_MODEL exclusions
    other_models = [m.internal_name for m in CORE_MODELS if m.internal_name != model]
    lines.append("    # model-specific: exclude unreachable INTERNAL_MODEL branches")
    for m in other_models:
        lines.append(rf'    if utils\.INTERNAL_MODEL == "{m}"')
        lines.append(rf'    elif utils\.INTERNAL_MODEL == "{m}"')
    lines.append(rf'    if utils\.INTERNAL_MODEL != "{model}"')

    lines.append("")  # trailing newline
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate model-specific .coveragerc")
    parser.add_argument("model", help="Trezor model (e.g. T2T1, T3B1, T3T1, T3W1)")
    args = parser.parse_args()

    if by_internal_name(args.model) is None:
        parser.error(f"Unknown model: {args.model}")

    flags = get_flag_values(args.model)
    content = generate_coveragerc(args.model, flags)

    output = CORE / f".coveragerc.{args.model}"
    output.write_text(content)
    print(f"Generated {output}")


if __name__ == "__main__":
    main()
