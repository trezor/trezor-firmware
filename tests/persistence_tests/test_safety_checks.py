import pytest

from trezorlib import debuglink, device
from trezorlib.messages import SafetyCheckLevel

from ..common import MNEMONIC12
from ..emulators import EmulatorWrapper
from ..upgrade_tests import core_only


@pytest.fixture
def emulator():
    with EmulatorWrapper("core") as emu:
        yield emu


@core_only
@pytest.mark.parametrize(
    "set_level,after_level",
    [
        (SafetyCheckLevel.Strict, SafetyCheckLevel.Strict),
        (SafetyCheckLevel.PromptTemporarily, SafetyCheckLevel.Strict),
        (SafetyCheckLevel.PromptAlways, SafetyCheckLevel.PromptAlways),
    ],
)
def test_safety_checks_level_after_reboot(emulator, set_level, after_level):
    device.wipe(emulator.client)
    debuglink.load_device(
        emulator.client,
        mnemonic=MNEMONIC12,
        pin="",
        passphrase_protection=False,
        label="SAFETYLEVEL",
    )

    device.apply_settings(emulator.client, safety_checks=set_level)
    assert emulator.client.features.safety_checks == set_level

    emulator.restart()

    assert emulator.client.features.safety_checks == after_level
