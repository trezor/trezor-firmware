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

from __future__ import annotations

from copy import deepcopy
from typing import Any, Iterator

import pytest

from trezorlib import debuglink, device, exceptions, messages, models
from trezorlib._internal import translations
from trezorlib.debuglink import SessionDebugWrapper as Session
from trezorlib.debuglink import TrezorClientDebugLink as Client
from trezorlib.debuglink import message_filters

from ..translations import (
    LANGUAGES,
    build_and_sign_blob,
    get_lang_json,
    prepare_blob,
    set_language,
    sign_blob,
)

pytestmark = pytest.mark.models("core", skip=["eckhart"])


MAX_DATA_LENGTH = {
    models.T2T1: 48 * 1024,
    models.T2B1: 32 * 1024,
    models.T3T1: 256 * 1024,
    models.T3B1: 256 * 1024,
    models.T3W1: 256 * 1024,  # FIXME: fill in correct value
}


def get_ping_button(lang: str) -> str:
    content = get_lang_json(lang)
    return content["translations"]["buttons__confirm"]


def get_ping_title(lang: str) -> str:
    content = get_lang_json(lang)
    return content["translations"]["words__confirm"]


@pytest.fixture
def session(session: Session) -> Iterator[Session]:
    lang_before = session.features.language or ""
    try:
        set_language(session, "en", force=True)
        yield session
    finally:
        set_language(session, lang_before[:2], force=True)


def _check_ping_screen_texts(session: Session, title: str, right_button: str) -> None:
    def ping_input_flow(session: Session, title: str, right_button: str):
        yield
        layout = session.client.debug.read_layout()
        assert layout.title().upper() == title.upper()
        assert layout.button_contents()[-1].upper() == right_button.upper()
        session.client.debug.press_yes()

    # TT does not have a right button text (but a green OK tick)
    if session.model in (models.T2T1, models.T3T1):
        right_button = "-"

    with session, session.client as client:
        client.watch_layout(True)
        client.set_input_flow(ping_input_flow(session, title, right_button))
        ping = session.call(messages.Ping(message="ahoj!", button_protection=True))
        assert ping == messages.Success(message="ahoj!")


def test_error_too_long(session: Session):
    assert session.features.language == "en-US"
    # Translations too long
    # Sending more than allowed by the flash capacity
    max_length = MAX_DATA_LENGTH[session.model]
    with pytest.raises(
        exceptions.TrezorFailure, match="Translations too long"
    ), session:
        bad_data = (max_length + 1) * b"a"
        device.change_language(session, language_data=bad_data)
    assert session.features.language == "en-US"
    _check_ping_screen_texts(session, get_ping_title("en"), get_ping_button("en"))


def test_error_invalid_data_length(session: Session):
    assert session.features.language == "en-US"
    # Invalid data length
    # Sending more data than advertised in the header
    with pytest.raises(exceptions.TrezorFailure, match="Invalid data length"), session:
        good_data = build_and_sign_blob("cs", session)
        bad_data = good_data + b"abcd"
        device.change_language(session, language_data=bad_data)
    assert session.features.language == "en-US"
    _check_ping_screen_texts(session, get_ping_title("en"), get_ping_button("en"))


def test_error_invalid_header_magic(session: Session):
    assert session.features.language == "en-US"
    # Invalid header magic
    # Does not match the expected magic
    with pytest.raises(
        exceptions.TrezorFailure, match="Invalid translations data"
    ), session:
        good_data = build_and_sign_blob("cs", session)
        bad_data = 4 * b"a" + good_data[4:]
        device.change_language(session, language_data=bad_data)
    assert session.features.language == "en-US"
    _check_ping_screen_texts(session, get_ping_title("en"), get_ping_button("en"))


def test_error_invalid_data_hash(session: Session):
    assert session.features.language == "en-US"
    # Invalid data hash
    # Changing the data after their hash has been calculated
    with pytest.raises(
        exceptions.TrezorFailure, match="Translation data verification failed"
    ), session:
        good_data = build_and_sign_blob("cs", session)
        bad_data = good_data[:-8] + 8 * b"a"
        device.change_language(
            session,
            language_data=bad_data,
        )
    assert session.features.language == "en-US"
    _check_ping_screen_texts(session, get_ping_title("en"), get_ping_button("en"))


def test_error_version_mismatch(session: Session):
    assert session.features.language == "en-US"
    # Translations version mismatch
    # Change the version to one not matching the current device
    with pytest.raises(
        exceptions.TrezorFailure, match="Translations version mismatch"
    ), session:
        blob = prepare_blob("cs", session.model, (3, 5, 4, 0))
        device.change_language(
            session,
            language_data=sign_blob(blob),
        )
    assert session.features.language == "en-US"
    _check_ping_screen_texts(session, get_ping_title("en"), get_ping_button("en"))


def test_error_invalid_signature(session: Session):
    assert session.features.language == "en-US"
    # Invalid signature
    # Changing the data in the signature section
    with pytest.raises(
        exceptions.TrezorFailure, match="Invalid translations data"
    ), session:
        blob = prepare_blob("cs", session.model, session.version)
        blob.proof = translations.Proof(
            merkle_proof=[],
            sigmask=0b011,
            signature=b"a" * 64,
        )
        device.change_language(
            session,
            language_data=blob.build(),
        )
    assert session.features.language == "en-US"
    _check_ping_screen_texts(session, get_ping_title("en"), get_ping_button("en"))


@pytest.mark.parametrize("lang", LANGUAGES)
def test_full_language_change(session: Session, lang: str):
    assert session.features.language == "en-US"
    assert session.features.language_version_matches is True

    # Setting selected language
    set_language(session, lang)
    assert session.features.language[:2] == lang
    assert session.features.language_version_matches is True
    _check_ping_screen_texts(session, get_ping_title(lang), get_ping_button(lang))

    # Setting the default language via empty data
    set_language(session, "en")
    assert session.features.language == "en-US"
    assert session.features.language_version_matches is True
    _check_ping_screen_texts(session, get_ping_title("en"), get_ping_button("en"))


def test_language_is_removed_after_wipe(client: Client):
    session = client.get_session()
    assert session.features.language == "en-US"

    _check_ping_screen_texts(session, get_ping_title("en"), get_ping_button("en"))

    # Setting cs language
    set_language(session, "cs")
    assert session.features.language == "cs-CZ"

    _check_ping_screen_texts(session, get_ping_title("cs"), get_ping_button("cs"))

    # Wipe device
    device.wipe(session)
    client = client.get_new_client()
    session = client.get_seedless_session()
    assert session.features.language == "en-US"

    # Load it again
    debuglink.load_device(
        session,
        mnemonic=" ".join(["all"] * 12),
        pin=None,
        passphrase_protection=False,
        label="test",
    )
    assert session.features.language == "en-US"

    _check_ping_screen_texts(session, get_ping_title("en"), get_ping_button("en"))


def test_translations_renders_on_screen(session: Session):

    czech_data = get_lang_json("cs")

    # Setting some values of words__confirm key and checking that in ping screen title
    assert session.features.language == "en-US"

    # Normal english
    _check_ping_screen_texts(session, get_ping_title("en"), get_ping_button("en"))
    # Normal czech
    set_language(session, "cs")

    assert session.features.language == "cs-CZ"
    _check_ping_screen_texts(session, get_ping_title("cs"), get_ping_button("cs"))

    # Modified czech - changed value
    czech_data_copy = deepcopy(czech_data)
    new_czech_confirm = "ABCD"
    czech_data_copy["translations"]["words__confirm"] = new_czech_confirm
    device.change_language(
        session,
        language_data=build_and_sign_blob(czech_data_copy, session),
    )
    _check_ping_screen_texts(session, new_czech_confirm, get_ping_button("cs"))

    # Modified czech - key deleted completely, english is shown
    czech_data_copy = deepcopy(czech_data)
    del czech_data_copy["translations"]["words__confirm"]
    device.change_language(
        session,
        language_data=build_and_sign_blob(czech_data_copy, session),
    )
    _check_ping_screen_texts(session, get_ping_title("en"), get_ping_button("cs"))


def test_reject_update(session: Session):

    assert session.features.language == "en-US"
    lang = "cs"
    language_data = build_and_sign_blob(lang, session)

    def input_flow_reject():
        yield
        session.client.debug.press_no()

    with pytest.raises(exceptions.Cancelled), session, session.client as client:
        client.set_input_flow(input_flow_reject)
        device.change_language(session, language_data)

    assert session.features.language == "en-US"

    _check_ping_screen_texts(session, get_ping_title("en"), get_ping_button("en"))


def _maybe_confirm_set_language(
    session: Session, lang: str, show_display: bool | None, is_displayed: bool
) -> None:
    language_data = build_and_sign_blob(lang, session)

    CHUNK_SIZE = 1024

    def chunks(data, size):
        for i in range(0, len(data), size):
            yield i, min(size, len(data) - i)

    expected_responses_silent: list[Any] = [
        messages.TranslationDataRequest(data_offset=off, data_length=len)
        for off, len in chunks(language_data, CHUNK_SIZE)
    ] + [message_filters.Success()]
    # , message_filters.Features()]

    expected_responses_confirm = expected_responses_silent[:]
    # confirmation after first TranslationDataRequest
    expected_responses_confirm.insert(1, message_filters.ButtonRequest())
    # success screen before Success / Features
    expected_responses_confirm.insert(-1, message_filters.ButtonRequest())

    if is_displayed:
        expected_responses = expected_responses_confirm
    else:
        expected_responses = expected_responses_silent

    with session:
        session.set_expected_responses(expected_responses)
        device.change_language(session, language_data, show_display=show_display)
        assert session.features.language is not None
        assert session.features.language[:2] == lang

        # explicitly handle the cases when expected_responses are correct for
        # change_language but incorrect for selected is_displayed mode (otherwise the
        # user would get an unhelpful generic expected_responses mismatch)
        if is_displayed and session.actual_responses == expected_responses_silent:
            raise AssertionError("Change should have been visible but was silent")
        if not is_displayed and session.actual_responses == expected_responses_confirm:
            raise AssertionError("Change should have been silent but was visible")
        # if the expected_responses do not match either, the generic error message will
        # be raised by the session context manager


@pytest.mark.parametrize(
    "show_display, is_displayed",
    [  # when device is not initialized, all combinations succeed.
        (True, True),
        (False, False),
        (None, False),  # default is False
    ],
)
@pytest.mark.setup_client(uninitialized=True)
@pytest.mark.uninitialized_session
def test_silent_first_install(session: Session, show_display: bool, is_displayed: bool):
    assert not session.features.initialized
    _maybe_confirm_set_language(session, "cs", show_display, is_displayed)


@pytest.mark.parametrize("show_display", (True, None))
def test_switch_from_english(session: Session, show_display: bool | None):
    assert session.features.initialized
    assert session.features.language == "en-US"
    _maybe_confirm_set_language(session, "cs", show_display, True)


def test_switch_from_english_not_silent(session: Session):
    assert session.features.initialized
    assert session.features.language == "en-US"
    with pytest.raises(
        exceptions.TrezorFailure, match="Cannot change language without user prompt"
    ):
        _maybe_confirm_set_language(session, "cs", False, False)


@pytest.mark.setup_client(uninitialized=True)
@pytest.mark.uninitialized_session
def test_switch_language(session: Session):
    assert not session.features.initialized
    assert session.features.language == "en-US"

    # switch to Czech silently
    _maybe_confirm_set_language(session, "cs", False, False)

    # switch to French silently
    with pytest.raises(
        exceptions.TrezorFailure, match="Cannot change language without user prompt"
    ):
        _maybe_confirm_set_language(session, "fr", False, False)

    # switch to French with display, explicitly
    _maybe_confirm_set_language(session, "fr", True, True)

    # switch back to Czech with display, implicitly
    _maybe_confirm_set_language(session, "cs", None, True)


def test_header_trailing_data(session: Session):
    """Adding trailing data to _header_ section specifically must be accepted by
    firmware, as long as the blob is otherwise valid and signed.

    (this ensures forwards compatibility if we extend the header)
    """

    assert session.features.language == "en-US"
    lang = "cs"
    blob = prepare_blob(lang, session.model, session.version)
    blob.header_bytes += b"trailing dataa"
    assert len(blob.header_bytes) % 2 == 0, "Trailing data must keep the 2-alignment"
    language_data = sign_blob(blob)

    device.change_language(session, language_data)
    assert session.features.language == "cs-CZ"
    _check_ping_screen_texts(session, get_ping_title(lang), get_ping_button(lang))
