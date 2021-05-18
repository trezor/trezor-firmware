from trezorlib import debuglink, device, messages

from ..common import MNEMONIC12
from ..emulators import EmulatorWrapper
from ..upgrade_tests import core_only, legacy_only

PIN = "1234"
WIPE_CODE = "9876"


def setup_device_legacy(client, pin, wipe_code):
    device.wipe(client)
    debuglink.load_device(
        client, MNEMONIC12, pin, passphrase_protection=False, label="WIPECODE"
    )

    with client:
        client.use_pin_sequence([PIN, WIPE_CODE, WIPE_CODE])
        device.change_wipe_code(client)


def setup_device_core(client, pin, wipe_code):
    device.wipe(client)
    debuglink.load_device(
        client, MNEMONIC12, pin, passphrase_protection=False, label="WIPECODE"
    )

    def input_flow():
        yield  # do you want to set/change the wipe_code?
        client.debug.press_yes()
        if pin is not None:
            yield  # enter current pin
            client.debug.input(pin)
        yield  # enter new wipe code
        client.debug.input(wipe_code)
        yield  # enter new wipe code again
        client.debug.input(wipe_code)
        yield  # success
        client.debug.press_yes()

    with client:
        client.set_expected_responses(
            [messages.ButtonRequest()] * 5 + [messages.Success, messages.Features]
        )
        client.set_input_flow(input_flow)
        device.change_wipe_code(client)


@core_only
def test_wipe_code_activate_core():
    with EmulatorWrapper("core") as emu:
        # set up device
        setup_device_core(emu.client, PIN, WIPE_CODE)

        emu.client.init_device()
        device_id = emu.client.features.device_id

        # Initiate Change pin process
        ret = emu.client.call_raw(messages.ChangePin(remove=False))
        assert isinstance(ret, messages.ButtonRequest)
        emu.client.debug.press_yes()
        ret = emu.client.call_raw(messages.ButtonAck())

        # Enter the wipe code instead of the current PIN
        assert ret == messages.ButtonRequest(code=messages.ButtonRequestType.PinEntry)
        emu.client._raw_write(messages.ButtonAck())
        emu.client.debug.input(WIPE_CODE)

        # wait 30 seconds for emulator to shut down
        # this will raise a TimeoutError if the emulator doesn't die.
        emu.wait(30)

        emu.start()
        assert emu.client.features.initialized is False
        assert emu.client.features.pin_protection is False
        assert emu.client.features.wipe_code_protection is False
        assert emu.client.features.device_id != device_id


@legacy_only
def test_wipe_code_activate_legacy():
    with EmulatorWrapper("legacy") as emu:
        # set up device
        setup_device_legacy(emu.client, PIN, WIPE_CODE)

        emu.client.init_device()
        device_id = emu.client.features.device_id

        # Initiate Change pin process
        ret = emu.client.call_raw(messages.ChangePin(remove=False))
        assert isinstance(ret, messages.ButtonRequest)
        emu.client.debug.press_yes()
        ret = emu.client.call_raw(messages.ButtonAck())

        # Enter the wipe code instead of the current PIN
        assert isinstance(ret, messages.PinMatrixRequest)
        wipe_code_encoded = emu.client.debug.encode_pin(WIPE_CODE)
        emu.client._raw_write(messages.PinMatrixAck(pin=wipe_code_encoded))

        # wait 30 seconds for emulator to shut down
        # this will raise a TimeoutError if the emulator doesn't die.
        emu.wait(30)

        emu.start()
        assert emu.client.features.initialized is False
        assert emu.client.features.pin_protection is False
        assert emu.client.features.wipe_code_protection is False
        assert emu.client.features.device_id != device_id
