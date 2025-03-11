import json
import re
import threading
import typing as t
import warnings
from hashlib import sha256
from pathlib import Path

from trezorlib import cosi, device, models
from trezorlib._internal import translations
from trezorlib.debuglink import LayoutType
from trezorlib.debuglink import TrezorClientDebugLink as Client

from . import common

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

TRANSLATIONS_DIR = ROOT / "core" / "translations"
FONTS_DIR = TRANSLATIONS_DIR / "fonts"
ORDER_FILE = TRANSLATIONS_DIR / "order.json"

LANGUAGES = [file.stem for file in TRANSLATIONS_DIR.glob("??.json")]

_CURRENT_TRANSLATION = threading.local()


def prepare_blob(
    lang_or_def: translations.JsonDef | Path | str,
    model: models.TrezorModel,
    version: translations.VersionTuple | tuple[int, int, int] | None = None,
) -> translations.TranslationsBlob:
    order = translations.order_from_json(json.loads(ORDER_FILE.read_text()))
    if isinstance(lang_or_def, str):
        lang_or_def = get_lang_json(lang_or_def)
    if isinstance(lang_or_def, Path):
        lang_or_def = t.cast(translations.JsonDef, json.loads(lang_or_def.read_text()))

    # generate raw blob
    if version is None:
        version = translations.version_from_json(lang_or_def["header"]["version"])
    elif len(version) == 3:
        # version coming from client object does not have build item
        version = *version, 0
    return translations.blob_from_defs(lang_or_def, order, model, version, FONTS_DIR)


def sign_blob(blob: translations.TranslationsBlob) -> bytes:
    # build 0-item Merkle proof
    digest = sha256(b"\x00" + blob.header_bytes).digest()
    signature = cosi.sign_with_privkeys(digest, common.PRIVATE_KEYS_DEV)
    blob.proof = translations.Proof(
        merkle_proof=[],
        sigmask=0b111,
        signature=signature,
    )
    return blob.build()


def build_and_sign_blob(
    lang_or_def: translations.JsonDef | Path | str,
    client: Client,
) -> bytes:
    blob = prepare_blob(lang_or_def, client.model, client.version)
    return sign_blob(blob)


def set_language(client: Client, lang: str, *, force: bool = False):
    if lang.startswith("en"):
        language_data = b""
    else:
        language_data = build_and_sign_blob(lang, client)
    with client:
        if not client.features.language.startswith(lang) or force:
            device.change_language(client, language_data)  # type: ignore
    _CURRENT_TRANSLATION.LAYOUT = client.layout_type
    _CURRENT_TRANSLATION.TR = TRANSLATIONS[lang]


def get_lang_json(lang: str) -> translations.JsonDef:
    assert lang in LANGUAGES
    lang_json = json.loads((TRANSLATIONS_DIR / f"{lang}.json").read_text())
    if (fonts_safe3 := lang_json.get("fonts", {}).get("##Safe3")) is not None:
        lang_json["fonts"]["T2B1"] = fonts_safe3
        lang_json["fonts"]["T3B1"] = fonts_safe3
    return lang_json


class Translation:
    FORMAT_STR_RE = re.compile(r"\\{\d+\\}")

    def __init__(self, lang: str) -> None:
        self.lang = lang
        self.lang_json = get_lang_json(lang)

    @property
    def translations(self) -> dict[str, str | dict[str, str]]:
        return self.lang_json["translations"]

    def _translate_raw(self, key: str, _stacklevel: int = 0) -> str:
        tr = self.translations.get(key)
        if tr is not None:
            # Handle layout-specific translations
            if isinstance(tr, dict) and hasattr(_CURRENT_TRANSLATION, "LAYOUT"):
                # Try to get translation for current layout
                layout_name = _CURRENT_TRANSLATION.LAYOUT.name
                if layout_name in tr:
                    return tr[layout_name]
                # Fall back to any available translation if no match for current layout
                return next(iter(tr.values()))
            elif isinstance(tr, str):
                return tr
            else:
                raise ValueError(f"Invalid translation value for key '{key}'")
        if self.lang != "en":
            # check if the key exists in English first
            retval = TRANSLATIONS["en"]._translate_raw(key)
            # if not, a KeyError was raised so we fall through.
            # otherwise, warn that the key is untranslated in target language.
            warnings.warn(
                f"Translation key '{key}' not found in '{self.lang}' translation file",
                stacklevel=_stacklevel + 2,
            )
            return retval
        raise KeyError(key)

    def translate(self, key: str, _stacklevel: int = 0) -> str:
        tr = self._translate_raw(key, _stacklevel=_stacklevel + 1)
        return tr.replace("\xa0", " ").strip()

    def as_regexp(self, key: str, _stacklevel: int = 0) -> re.Pattern:
        tr = self.translate(key, _stacklevel=_stacklevel + 1)
        re_safe = re.escape(tr)
        return re.compile(self.FORMAT_STR_RE.sub(r".*?", re_safe))


TRANSLATIONS = {lang: Translation(lang) for lang in LANGUAGES}
_CURRENT_TRANSLATION.TR = TRANSLATIONS["en"]
_CURRENT_TRANSLATION.LAYOUT = LayoutType.Bolt


def translate(key: str, _stacklevel: int = 0) -> str:
    return _CURRENT_TRANSLATION.TR.translate(key, _stacklevel=_stacklevel + 1)


def regexp(key: str) -> re.Pattern:
    return _CURRENT_TRANSLATION.TR.as_regexp(key, _stacklevel=1)


def __getattr__(key: str) -> str:
    try:
        return translate(key, _stacklevel=1)
    except KeyError as e:
        raise AttributeError(f"Translation key '{key}' not found") from e
