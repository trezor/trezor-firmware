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
from trezorlib._internal import translations
from trezorlib.debuglink import TrezorClientDebugLink as Client

from ..translations import (
    LANGUAGES,
    get_lang_json,
    set_language,
    build_and_sign_blob,
)

pytestmark = pytest.mark.skip_t1


MAX_DATA_LENGTH = {models.T2T1: 48 * 1024, models.T2B1: 32 * 1024}


def get_confirm(lang: str) -> str:
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
        assert layout.title() == title.upper()
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


def test_change_language_errors(client: Client):
    assert client.features.language == "enUS"

    # Translations too short
    # Sending less data than the header length
    with pytest.raises(
        exceptions.TrezorFailure, match="Translations too short"
    ), client:
        bad_data = (translations.HEADER_LEN - 1) * b"a"
        device.change_language(client, language_data=bad_data)
    assert client.features.language == "enUS"

    # Translations too long
    # Sending more than allowed by the flash capacity
    max_length = MAX_DATA_LENGTH[client.model]
    with pytest.raises(exceptions.TrezorFailure, match="Translations too long"), client:
        bad_data = (max_length + 1) * b"a"
        device.change_language(client, language_data=bad_data)
    assert client.features.language == "enUS"

    # Invalid header data length
    # Sending more data than advertised in the header
    with pytest.raises(
        exceptions.TrezorFailure, match="Invalid header data length"
    ), client:
        good_data = build_and_sign_blob("cs", client.model)
        bad_data = good_data + b"abcd"
        device.change_language(client, language_data=bad_data)
    assert client.features.language == "enUS"

    # Invalid header magic
    # Does not match the expected magic
    with pytest.raises(exceptions.TrezorFailure, match="Invalid header magic"), client:
        good_data = build_and_sign_blob("cs", client.model)
        bad_data = 4 * b"a" + good_data[4:]
        device.change_language(client, language_data=bad_data)
    assert client.features.language == "enUS"

    # Invalid header data
    # Putting non-zero bytes where zero is expected
    with pytest.raises(exceptions.TrezorFailure, match="Invalid header data"), client:
        good_data = build_and_sign_blob("cs", client.model)
        pre_sig_pos = translations.HEADER_LEN - translations.SIG_LEN
        bad_data = good_data[: pre_sig_pos - 4] + 4 * b"a" + good_data[pre_sig_pos:]
        device.change_language(
            client,
            language_data=bad_data,
        )
    assert client.features.language == "enUS"

    # Invalid data hash
    # Changing the data after their hash has been calculated
    with pytest.raises(exceptions.TrezorFailure, match="Invalid data hash"), client:
        good_data = build_and_sign_blob("cs", client.model)
        bad_data = good_data[:-8] + 8 * b"a"
        device.change_language(
            client,
            language_data=bad_data,
        )
    assert client.features.language == "enUS"

    # Invalid translations version
    # Change the version to one not matching the current device
    with pytest.raises(
        exceptions.TrezorFailure, match="Invalid translations version"
    ), client:
        data = get_lang_json("cs")
        data["header"]["version"] = "3.5.4"
        device.change_language(
            client,
            language_data=build_and_sign_blob(data, client.model),
        )
    assert client.features.language == "enUS"

    # Invalid header version
    # Version is not a valid semver with integers
    with pytest.raises(
        exceptions.TrezorFailure, match="Invalid header version"
    ), client:
        data = get_lang_json("cs")
        data["header"]["version"] = "ABC.XYZ.DEF"
        device.change_language(
            client,
            language_data=build_and_sign_blob(data, client.model),
        )
    assert client.features.language == "enUS"

    # Invalid translations signature
    # Modifying the signature part of the header
    with pytest.raises(
        exceptions.TrezorFailure, match="Invalid translations signature"
    ), client:
        good_data = translations.blob_from_file(
            get_lang_json("cs"), client.features.model or ""
        )
        bad_data = (
            good_data[: translations.HEADER_LEN - 8]
            + 8 * b"a"
            + good_data[translations.HEADER_LEN :]
        )
        device.change_language(
            client,
            language_data=bad_data,
        )
    assert client.features.language == "enUS"

    _check_ping_screen_texts(client, get_confirm("en"), get_confirm("en"))


@pytest.mark.parametrize("lang", LANGUAGES)
def test_full_language_change(client: Client, lang: str):
    assert client.features.language == "enUS"

    # Setting selected language
    set_language(client, lang)
    assert client.features.language[:2] == lang
    _check_ping_screen_texts(client, get_confirm(lang), get_confirm(lang))

    # Setting the default language via empty data
    set_language(client, "en")
    assert client.features.language == "enUS"
    _check_ping_screen_texts(client, get_confirm("en"), get_confirm("en"))


def test_language_stays_after_wipe(client: Client):
    assert client.features.language == "enUS"

    _check_ping_screen_texts(client, get_confirm("en"), get_confirm("en"))

    # Setting cs language
    set_language(client, "cs")
    assert client.features.language == "csCZ"

    _check_ping_screen_texts(client, get_confirm("cs"), get_confirm("cs"))

    # Wipe device
    device.wipe(client)
    assert client.features.language == "csCZ"

    # Load it again
    debuglink.load_device(
        client,
        mnemonic=" ".join(["all"] * 12),
        pin=None,
        passphrase_protection=False,
        label="test",
    )
    assert client.features.language == "csCZ"

    _check_ping_screen_texts(client, get_confirm("cs"), get_confirm("cs"))


def test_translations_renders_on_screen(client: Client):
    czech_data = get_lang_json("cs")

    # Setting some values of words__confirm key and checking that in ping screen title
    assert client.features.language == "enUS"

    # Normal english
    _check_ping_screen_texts(client, get_confirm("en"), get_confirm("en"))

    # Normal czech
    set_language(client, "cs")
    assert client.features.language == "csCZ"
    _check_ping_screen_texts(client, get_confirm("cs"), get_confirm("cs"))

    # Modified czech - changed value
    czech_data_copy = deepcopy(czech_data)
    new_czech_confirm = "ABCD"
    czech_data_copy["translations"]["words__confirm"] = new_czech_confirm
    device.change_language(
        client,
        language_data=build_and_sign_blob(czech_data_copy, client.model),
    )
    _check_ping_screen_texts(client, new_czech_confirm, get_confirm("cs"))

    # Modified czech - key deleted completely, english is shown
    czech_data_copy = deepcopy(czech_data)
    del czech_data_copy["translations"]["words__confirm"]
    device.change_language(
        client,
        language_data=build_and_sign_blob(czech_data_copy, client.model),
    )
    _check_ping_screen_texts(client, get_confirm("en"), get_confirm("cs"))
