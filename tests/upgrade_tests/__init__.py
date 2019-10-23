import os

import pytest

from ..emulators import EmulatorWrapper

SELECTED_GENS = [
    gen.strip() for gen in os.environ.get("TREZOR_UPGRADE_TEST", "").split(",") if gen
]

if SELECTED_GENS:
    # if any gens were selected via the environment variable, force enable all selected
    LEGACY_ENABLED = "legacy" in SELECTED_GENS
    CORE_ENABLED = "core" in SELECTED_GENS

else:
    # if no selection was provided, select those for which we have emulators
    try:
        EmulatorWrapper("legacy")
        LEGACY_ENABLED = True
    except Exception:
        LEGACY_ENABLED = False

    try:
        EmulatorWrapper("core")
        CORE_ENABLED = True
    except Exception:
        CORE_ENABLED = False


legacy_only = pytest.mark.skipif(
    not LEGACY_ENABLED, reason="This test requires legacy emulator"
)

core_only = pytest.mark.skipif(
    not CORE_ENABLED, reason="This test requires core emulator"
)
