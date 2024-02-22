# This file is part of the Trezor project.
#
# Copyright (C) 2012-2019 SatoshiLabs and contributors
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version 3
# as published by the Free Software Foundation.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the License along with this library.
# If not, see <https://www.gnu.org/licenses/lgpl-3.0.html>.

from copy import deepcopy
from typing import Iterator

import pytest

from trezorlib import debuglink, device, exceptions, messages, models
from trezorlib.debuglink import TrezorClientDebugLink as Client

from ..translations import LANGUAGES, build_and_sign_blob, get_lang_json, set_language

pytestmark = pytest.mark.skip_t1


MAX_DATA_LENGTH = {models.T2T1: 48 * 1024, models.T2B1: 32 * 1024}


def get_ping_button(lang: str) -> str:
    content = get_lang_json(lang)
    return content["translations"]["buttons__confirm"]


def get_ping_title(lang: str) -> str:
    content = get_lang_json(lang)
    return content["translations"]["words__confirm"]


@pytest.fixture
def client(client: Client) -> Iterator[Client]:
    lang_before = client.features.language or ""
    try:
        set_language(client, "en")
        yield client
    finally:
        set_language(client, lang_before[:2])


def _check_ping_screen_texts(client: Client, title: str, right_button: str) -> None:
    def ping_input_flow(client: Client, title: str, right_button: str):
        yield
        layout = client.debug.wait_layout()
        assert layout.title().upper() == title.upper()
        assert layout.button_contents()[-1] == right_button.upper()
        client.debug.press_yes()

    # TT does not have a right button text (but a green OK tick)
    if client.features.model == "T":
        right_button = "-"

    with client:
        client.watch_layout(True)
        client.set_input_flow(ping_input_flow(client, title, right_button))
        ping = client.call(messages.Ping(message="ahoj!", button_protection=True))
        assert ping == messages.Success(message="ahoj!")


def test_error_too_long(client: Client):
    assert client.features.language == "en-US"
    # Translations too long
    # Sending more than allowed by the flash capacity
    max_length = MAX_DATA_LENGTH[client.model]
    with pytest.raises(exceptions.TrezorFailure, match="Translations too long"), client:
        bad_data = (max_length + 1) * b"a"
        device.change_language(client, language_data=bad_data)
    assert client.features.language == "en-US"
    _check_ping_screen_texts(client, get_ping_title("en"), get_ping_button("en"))


def test_error_invalid_data_length(client: Client):
    assert client.features.language == "en-US"
    # Invalid data length
    # Sending more data than advertised in the header
    with pytest.raises(exceptions.TrezorFailure, match="Invalid data length"), client:
        good_data = build_and_sign_blob("cs", client.model)
        bad_data = good_data + b"abcd"
        device.change_language(client, language_data=bad_data)
    assert client.features.language == "en-US"
    _check_ping_screen_texts(client, get_ping_title("en"), get_ping_button("en"))


def test_error_invalid_header_magic(client: Client):
    assert client.features.language == "en-US"
    # Invalid header magic
    # Does not match the expected magic
    with pytest.raises(
        exceptions.TrezorFailure, match="Invalid translations data"
    ), client:
        good_data = build_and_sign_blob("cs", client.model)
        bad_data = 4 * b"a" + good_data[4:]
        device.change_language(client, language_data=bad_data)
    assert client.features.language == "en-US"
    _check_ping_screen_texts(client, get_ping_title("en"), get_ping_button("en"))


def test_error_invalid_data_hash(client: Client):
    assert client.features.language == "en-US"
    # Invalid data hash
    # Changing the data after their hash has been calculated
    with pytest.raises(
        exceptions.TrezorFailure, match="Translation data verification failed"
    ), client:
        good_data = build_and_sign_blob("cs", client.model)
        bad_data = good_data[:-8] + 8 * b"a"
        device.change_language(
            client,
            language_data=bad_data,
        )
    assert client.features.language == "en-US"
    _check_ping_screen_texts(client, get_ping_title("en"), get_ping_button("en"))


def test_error_version_mismatch(client: Client):
    assert client.features.language == "en-US"
    # Translations version mismatch
    # Change the version to one not matching the current device
    with pytest.raises(
        exceptions.TrezorFailure, match="Translations version mismatch"
    ), client:
        data = get_lang_json("cs")
        data["header"]["version"] = "3.5.4"
        device.change_language(
            client,
            language_data=build_and_sign_blob(data, client.model),
        )
    assert client.features.language == "en-US"
    _check_ping_screen_texts(client, get_ping_title("en"), get_ping_button("en"))


def test_error_invalid_header_version(client: Client):
    assert client.features.language == "en-US"
    # Invalid header version
    # Version is not a valid semver with integers
    with pytest.raises(ValueError), client:
        data = get_lang_json("cs")
        data["header"]["version"] = "ABC.XYZ.DEF"
        device.change_language(
            client,
            language_data=build_and_sign_blob(data, client.model),
        )
    assert client.features.language == "en-US"
    _check_ping_screen_texts(client, get_ping_title("en"), get_ping_button("en"))


def test_error_invalid_signature(client: Client):
    assert client.features.language == "en-US"
    # Invalid signature
    # Changing the data in the signature section
    with pytest.raises(
        exceptions.TrezorFailure, match="Invalid translations data"
    ), client:
        good_data = bytearray(build_and_sign_blob("cs", client.model))
        bad_data = bytearray(good_data)
        bad_data[128:256] = 128 * b"a"
        device.change_language(
            client,
            language_data=bytes(bad_data),
        )
    assert client.features.language == "en-US"
    _check_ping_screen_texts(client, get_ping_title("en"), get_ping_button("en"))


@pytest.mark.parametrize("lang", LANGUAGES)
def test_full_language_change(client: Client, lang: str):
    assert client.features.language == "en-US"
    assert client.features.language_version_matches is True

    # Setting selected language
    set_language(client, lang)
    assert client.features.language[:2] == lang
    assert client.features.language_version_matches is True
    _check_ping_screen_texts(client, get_ping_title(lang), get_ping_button(lang))

    # Setting the default language via empty data
    set_language(client, "en")
    assert client.features.language == "en-US"
    assert client.features.language_version_matches is True
    _check_ping_screen_texts(client, get_ping_title("en"), get_ping_button("en"))


def test_language_is_removed_after_wipe(client: Client):
    assert client.features.language == "en-US"

    _check_ping_screen_texts(client, get_ping_title("en"), get_ping_button("en"))

    # Setting cs language
    set_language(client, "cs")
    assert client.features.language == "cs-CZ"

    _check_ping_screen_texts(client, get_ping_title("cs"), get_ping_button("cs"))

    # Wipe device
    device.wipe(client)
    assert client.features.language == "en-US"

    # Load it again
    debuglink.load_device(
        client,
        mnemonic=" ".join(["all"] * 12),
        pin=None,
        passphrase_protection=False,
        label="test",
    )
    assert client.features.language == "en-US"

    _check_ping_screen_texts(client, get_ping_title("en"), get_ping_button("en"))


def test_translations_renders_on_screen(client: Client):
    czech_data = get_lang_json("cs")

    # Setting some values of words__confirm key and checking that in ping screen title
    assert client.features.language == "en-US"

    # Normal english
    _check_ping_screen_texts(client, get_ping_title("en"), get_ping_button("en"))

    # Normal czech
    set_language(client, "cs")
    assert client.features.language == "cs-CZ"
    _check_ping_screen_texts(client, get_ping_title("cs"), get_ping_button("cs"))

    # Modified czech - changed value
    czech_data_copy = deepcopy(czech_data)
    new_czech_confirm = "ABCD"
    czech_data_copy["translations"]["words__confirm"] = new_czech_confirm
    device.change_language(
        client,
        language_data=build_and_sign_blob(czech_data_copy, client.model),
    )
    _check_ping_screen_texts(client, new_czech_confirm, get_ping_button("cs"))

    # Modified czech - key deleted completely, english is shown
    czech_data_copy = deepcopy(czech_data)
    del czech_data_copy["translations"]["words__confirm"]
    device.change_language(
        client,
        language_data=build_and_sign_blob(czech_data_copy, client.model),
    )
    _check_ping_screen_texts(client, get_ping_title("en"), get_ping_button("cs"))


def test_reject_update(client: Client):
    assert client.features.language == "en-US"
    lang = "cs"
    language_data = build_and_sign_blob(lang, client.model)

    def input_flow_reject():
        yield
        client.debug.press_no()

    with pytest.raises(exceptions.Cancelled), client:
        client.set_input_flow(input_flow_reject)
        device.change_language(client, language_data)

    assert client.features.language == "en-US"

    _check_ping_screen_texts(client, get_ping_title("en"), get_ping_button("en"))


def test_silent_update(client: Client):
    assert client.features.language == "en-US"
    lang = "cs"
    language_data = build_and_sign_blob(lang, client.model)

    def input_flow_confirm(language: str):
        if language == "cs":
            title = "NASTAVENÍ JAZYKA"
            text = "Změnit jazyk na cs-CZ?"
        else:
            title = "LANGUAGE SETTINGS"
            text = "Change language to cs-CZ?"

        def input_flow():
            yield
            layout = client.debug.wait_layout()
            assert layout.title() == title
            assert layout.text_content() == text
            client.debug.press_yes()

            yield
            layout = client.debug.wait_layout()
            assert layout.text_content() == "Jazyk byl úspěšně změněn"
            client.debug.press_yes()

        return input_flow

    def input_flow_silent():
        yield
        # It will never reach this - there is just loader on the screen
        assert False

    # Device is loaded with seed, language change is shown on the screen
    with client:
        client.watch_layout(True)
        client.set_input_flow(input_flow_confirm("en"))
        device.change_language(client, language_data)
        assert client.features.language[:2] == lang

    device.wipe(client)
    assert client.features.language == "en-US"

    # Device is empty, language is changed silently
    with client:
        client.watch_layout(True)
        client.set_input_flow(input_flow_silent)
        device.change_language(client, language_data)
        assert client.features.language[:2] == lang

    # Same language is set again, shown on screen
    with client:
        client.watch_layout(True)
        client.set_input_flow(input_flow_confirm("cs"))
        device.change_language(client, language_data)
        assert client.features.language[:2] == lang

    device.wipe(client)
    assert client.features.language == "en-US"

    debuglink.load_device(
        client,
        mnemonic=" ".join(["all"] * 12),
        pin=None,
        passphrase_protection=False,
        label="test",
    )

    # Device is again loaded with seed, language change is shown on the screen
    with client:
        client.watch_layout(True)
        client.set_input_flow(input_flow_confirm("en"))
        device.change_language(client, language_data)
        assert client.features.language[:2] == lang

    _check_ping_screen_texts(client, get_ping_title(lang), get_ping_button(lang))
