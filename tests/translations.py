import json
import typing as t
from hashlib import sha256
from pathlib import Path

from trezorlib import cosi, device, models
from trezorlib._internal import translations
from trezorlib.debuglink import TrezorClientDebugLink as Client

from . import common

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

TRANSLATIONS = ROOT / "core" / "translations"
FONTS_DIR = TRANSLATIONS / "fonts"
ORDER_FILE = TRANSLATIONS / "order.json"

LANGUAGES = [file.stem for file in TRANSLATIONS.glob("??.json")]


def build_and_sign_blob(
    lang_or_def: translations.JsonDef | Path | str,
    model: models.TrezorModel,
) -> bytes:
    order = translations.order_from_json(json.loads(ORDER_FILE.read_text()))
    if isinstance(lang_or_def, str):
        lang_or_def = get_lang_json(lang_or_def)
    if isinstance(lang_or_def, Path):
        lang_or_def = t.cast(translations.JsonDef, json.loads(lang_or_def.read_text()))

    # generate raw blob
    version = translations.version_from_json(lang_or_def["header"]["version"])
    blob = translations.blob_from_defs(lang_or_def, order, model, version, FONTS_DIR)

    # build 0-item Merkle proof
    digest = sha256(b"\x00" + blob.header_bytes).digest()
    signature = cosi.sign_with_privkeys(digest, common.PRIVATE_KEYS_DEV)
    blob.proof = translations.Proof(
        merkle_proof=[],
        sigmask=0b111,
        signature=signature,
    )
    return blob.build()


def set_language(client: Client, lang: str):
    if lang.startswith("en"):
        language_data = b""
    else:
        language_data = build_and_sign_blob(lang, client.model)
    with client:
        device.change_language(client, language_data)  # type: ignore


def get_lang_json(lang: str) -> translations.JsonDef:
    assert lang in LANGUAGES
    return json.loads((TRANSLATIONS / f"{lang}.json").read_text())


def _get_all_language_data() -> list[dict[str, str]]:
    return [_get_language_data(language) for language in LANGUAGES]


def _get_language_data(lang: str) -> dict[str, str]:
    return get_lang_json(lang)["translations"]


all_language_data = _get_all_language_data()


def _resolve_path_to_texts(
    path: str, template: t.Iterable[t.Any] = (), lower: bool = True
) -> list[str]:
    texts: list[str] = []
    lookups = path.split(".")
    for language_data in all_language_data:
        data: dict[str, t.Any] | str = language_data
        for lookup in lookups:
            assert isinstance(data, dict), f"{lookup} is not a dict"
            data = data[lookup]
        assert isinstance(data, str), f"{path} is not a string"
        if template:
            data = data.format(*template)
        texts.append(data)

    if lower:
        texts = [t.lower() for t in texts]
    texts = [t.strip() for t in texts]
    return texts


def assert_equals(text: str, path: str, template: t.Iterable[t.Any] = ()) -> None:
    # TODO: we can directly pass in the current device language
    texts = _resolve_path_to_texts(path, template)
    assert text.lower() in texts, f"{text} not found in {texts}"


def assert_equals_multiple(
    text: str, paths: list[str], template: t.Iterable[t.Any] = ()
) -> None:
    texts: list[str] = []
    for path in paths:
        texts += _resolve_path_to_texts(path, template)
    assert text.lower() in texts, f"{text} not found in {texts}"


def assert_in(text: str, path: str, template: t.Iterable[t.Any] = ()) -> None:
    texts = _resolve_path_to_texts(path, template)
    for tt in texts:
        if tt in text.lower():
            return
    assert False, f"{text} not found in {texts}"


def assert_startswith(text: str, path: str, template: t.Iterable[t.Any] = ()) -> None:
    texts = _resolve_path_to_texts(path, template)
    for tt in texts:
        if text.lower().startswith(tt):
            return
    assert False, f"{text} not found in {texts}"


def assert_template(text: str, template_path: str) -> None:
    templates = _resolve_path_to_texts(template_path)
    for tt in templates:
        # Checking at least the first part
        first_part = tt.split("{")[0]
        if text.lower().startswith(first_part):
            return
    assert False, f"{text} not found in {templates}"


def translate(
    path: str, template: t.Iterable[t.Any] = (), lower: bool = False
) -> list[str]:
    # Do not converting to lowercase, we want the exact value
    return _resolve_path_to_texts(path, template, lower=lower)
