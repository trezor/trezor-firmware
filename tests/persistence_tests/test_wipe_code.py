from trezorlib import debuglink, device, messages
from trezorlib.debuglink import TrezorClientDebugLink as Client
from trezorlib.debuglink import message_filters

from ..common import MNEMONIC12
from ..emulators import Emulator, EmulatorWrapper
from ..upgrade_tests import core_only, legacy_only

PIN = "1234"
WIPE_CODE = "9876"


def setup_device_legacy(client: Client, pin: str, wipe_code: str) -> None:
    session = client.get_seedless_session()
    device.wipe(session)
    client = client.get_new_client()
    session = client.get_seedless_session()
    debuglink.load_device(
        session,
        MNEMONIC12,
        pin,
        passphrase_protection=False,
        label="WIPECODE",
    )

    with session.client as client:
        client.use_pin_sequence([PIN, WIPE_CODE, WIPE_CODE])
        device.change_wipe_code(client.get_seedless_session())


def setup_device_core(client: Client, pin: str, wipe_code: str) -> None:
    session = client.get_seedless_session()
    device.wipe(session)
    client = client.get_new_client()
    session = client.get_seedless_session()
    debuglink.load_device(
        session,
        MNEMONIC12,
        pin,
        passphrase_protection=False,
        label="WIPECODE",
    )

    with session.client as client:
        client.use_pin_sequence([pin, wipe_code, wipe_code])
        device.change_wipe_code(client.get_seedless_session())


@core_only
def test_wipe_code_activate_core(core_emulator: Emulator):
    # set up device
    setup_device_core(core_emulator.client, PIN, WIPE_CODE)
    session = core_emulator.client.get_session()
    device_id = core_emulator.client.features.device_id

    # Initiate Change pin process
    ret = session.call_raw(messages.ChangePin(remove=False))
    assert isinstance(ret, messages.ButtonRequest)
    assert ret.name == "change_pin"
    core_emulator.client.debug.press_yes()
    ret = session.call_raw(messages.ButtonAck())

    # Enter the wipe code instead of the current PIN
    expected = message_filters.ButtonRequest(code=messages.ButtonRequestType.PinEntry)
    assert expected.match(ret)
    session._write(messages.ButtonAck())
    core_emulator.client.debug.input(WIPE_CODE)

    # preserving screenshots even after it dies and starts again
    prev_screenshot_dir = core_emulator.client.debug.screenshot_recording_dir

    # wait 30 seconds for emulator to shut down
    # this will raise a TimeoutError if the emulator doesn't die.
    core_emulator.wait(30)

    core_emulator.start()
    if prev_screenshot_dir:
        core_emulator.client.debug.start_recording(prev_screenshot_dir, refresh_index=1)
    assert core_emulator.client.features.initialized is False
    assert core_emulator.client.features.pin_protection is False
    assert core_emulator.client.features.wipe_code_protection is False
    assert core_emulator.client.features.device_id != device_id


@legacy_only
def test_wipe_code_activate_legacy():
    with EmulatorWrapper("legacy") as emu:
        # set up device
        setup_device_legacy(emu.client, PIN, WIPE_CODE)

        session = emu.client.get_session()
        device_id = emu.client.features.device_id

        # Initiate Change pin process
        ret = session.call_raw(messages.ChangePin(remove=False))
        assert isinstance(ret, messages.ButtonRequest)
        emu.client.debug.press_yes()
        ret = session.call_raw(messages.ButtonAck())

        # Enter the wipe code instead of the current PIN
        assert isinstance(ret, messages.PinMatrixRequest)
        wipe_code_encoded = emu.client.debug.encode_pin(WIPE_CODE)
        session._write(messages.PinMatrixAck(pin=wipe_code_encoded))

        # wait 30 seconds for emulator to shut down
        # this will raise a TimeoutError if the emulator doesn't die.
        emu.wait(30)

        emu.start()
        emu.client.refresh_features()
        assert emu.client.features.initialized is False
        assert emu.client.features.pin_protection is False
        assert emu.client.features.wipe_code_protection is False
        assert emu.client.features.device_id != device_id
