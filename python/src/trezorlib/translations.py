from __future__ import annotations

import json
import struct
import typing as t
import unicodedata
from hashlib import sha256
from pathlib import Path
from typing_extensions import Self

import construct as c
import requests
from construct_classes import Struct, subcon
from typing_extensions import TypedDict

from .translations_dev_sign import sign_with_dev_keys
from .tools import TupleAdapter

# All sections need to be aligned to 2 bytes for the offset tables using u16 to work properly
ALIGNMENT = 2
HEADER_MAX_LEN = 128
HEADER_WLEN = 256
SIG_LEN = 65
# TODO: why is the sigmask used/useful?
SIGMASK = (0b111).to_bytes(1, "little")

JsonTranslationData = dict[str, dict[str, str]]
JsonHeaderData = dict[str, str]
JsonFontData = dict[str, str]
JsonOrderData = dict[int, str]


def _normalize(what: str) -> str:
    return unicodedata.normalize("NFKC", what)


def offsets_seq(data: t.Iterable[bytes]) -> t.Iterator[int]:
    offset = 0
    for item in data:
        yield offset
        offset += len(item)
    yield offset


def _version_to_tuple(version: str) -> tuple[int, int, int, int]:
    items = [int(n) for n in version.split(".")]
    assert len(items) == 3
    return (*items, 0)  # type: ignore

class TranslationsHeader(Struct):
    language: str
    version: tuple[int, int, int, int]
    data_len: int
    translations_count: int
    fonts_offset: int
    data_hash: bytes
    change_language_title: str
    change_language_prompt: str

    # fmt: off
    SUBCON = c.Struct(
        "_start_offset" / c.Tell,
        "magic" / c.Const(b"TRTR"),
        "language" / c.PaddedString(2, "ascii"),
        "version" / TupleAdapter(c.Int8ul, c.Int8ul, c.Int8ul, c.Int8ul),
        "data_len" / c.Int16ul,
        "translations_count" / c.Int16ul,
        "fonts_offset" / c.Int16ul,
        "data_hash" / c.Bytes(32),
        "change_language_title" / c.PascalString(c.Int8ul, "utf8"),
        "change_language_prompt" / c.PascalString(c.Int8ul, "utf8"),
        "_end_offset" / c.Tell,

        "_maxlen" / c.Check(c.this._end_offset - c.this._start_offset <= HEADER_MAX_LEN),
    )
    # fmt: on


class TranslationsSignedHeader(Struct):
    header_bytes: bytes
    merkle_proof: list[bytes]
    sigmask: int
    signature: bytes

    header: TranslationsHeader = subcon(TranslationsHeader)

    # fmt: off
    SUBCON = c.Struct(
        "header_bytes" / c.Padded(c.Bytes(HEADER_MAX_LEN), HEADER_MAX_LEN),
        "merkle_proof" / c.PrefixedArray(c.Int8ul, c.Bytes(32)),
        "sigmask" / c.Int8ul,
        "signature" / c.Bytes(64),

        "header" / c.RestreamData(c.this.header_bytes, TranslationsHeader.SUBCON),
    )
    # fmt: on

    def __setattr__(self, name: str, value: t.Any) -> None:
        if name == "header_bytes":
            raise AttributeError("Cannot set header_bytes directly")
        super().__setattr__(name, value)
        if name == "header":
            super().__setattr__("header_bytes", value.build())


class BlobTable(Struct):
    length: int
    offsets: list[tuple[int, int]]
    data: bytes

    # fmt: off
    SUBCON = c.Struct(
        "length" / c.Int16ul,
        "offsets" / c.Array(c.this.length + 1, TupleAdapter(c.Int16ul, c.Int16ul)),
        "data" / c.GreedyBytes,
    )
    # fmt: on

    SENTINEL: t.ClassVar[int] = 0xFFFF

    @classmethod
    def from_items(cls, items: dict[int, bytes]) -> Self:
        keys = sorted(items.keys()) + [cls.SENTINEL]
        items_sorted = [items[key] for key in keys]
        offsets = list(offsets_seq(items_sorted))
        assert len(keys) == len(offsets)
        return cls(
            length=len(items),
            offsets=list(zip(keys, offsets)),
            data=b"".join(items_sorted),
        )

    def get(self, id: int) -> bytes | None:
        if id == self.SENTINEL:
            return None
        for key, offset in self.offsets:
            if key == id:
                return self.data[offset : self.offsets[key + 1][1]]
        return None


class TranslationData(Struct):
    offsets: list[int]
    strings: bytes

    # fmt: off
    SUBCON = c.Struct(
        "offsets" / c.GreedyRange(c.Int16ul),
        "strings" / c.GreedyBytes,
    )
    # fmt: on

    @classmethod
    def from_items(cls, items: list[str]) -> Self:
        item_bytes = [_normalize(item).encode("utf-8") for item in items]
        offsets = list(offsets_seq(item_bytes))
        return cls(offsets=offsets, strings=b"".join(item_bytes))

    def __len__(self) -> int:
        return len(self.offsets) - 1

    def get(self, idx: int) -> str | None:
        if idx >= len(self.offsets) - 1:
            return None
        return self.strings[self.offsets[idx] : self.offsets[idx + 1]].decode("utf-8")


class FileInfo(TypedDict):
    language: str
    version: str
    supported_models: list[str]


# TODO: might create some tests for reading the resulting blob
# TODO: try to apply some compression of the blob


class Signing:
    def __init__(self, data_without_sig: bytes) -> None:
        self.data_without_sig = data_without_sig

    def perform_dev_signing(self) -> bytes:
        """Signs the appropriate data and returns the blob with the signature"""
        signature = self._get_dev_signature()
        return self.apply_signature(signature)

    def _get_dev_signature(self) -> bytes:
        """Returns the development signature of the data."""
        to_sign = self.hash_to_sign()
        return sign_with_dev_keys(to_sign)

    def hash_to_sign(self) -> bytes:
        """Returns the data that should be signed - hash of header with empty signature."""
        data_to_sign = self.data_without_sig[:HEADER_LEN]
        for byte in data_to_sign[-SIG_LEN:]:
            assert byte == 0, "Signature should be empty"
        return sha256(data_to_sign).digest()

    def apply_signature(self, signature: bytes) -> bytes:
        """Put signature data at the right location into the header."""
        assert len(signature) == SIG_LEN - 1, "Signature should be 64 bytes long"
        to_write = SIGMASK + signature
        assert len(to_write) == SIG_LEN, "Signature and sigmask should be 65 bytes long"
        return (
            self.data_without_sig[: HEADER_LEN - SIG_LEN]
            + to_write
            + self.data_without_sig[HEADER_LEN:]
        )


def get_file_info(json_file: Path) -> FileInfo:
    with open(json_file, "r") as f:
        data = json.load(f)
    header: JsonHeaderData = data["header"]
    font = data["font"]

    supported_models = list(font.keys())
    return {
        "language": header["language"],
        "version": header["version"],
        "supported_models": supported_models,
    }


def blob_from_file(json_file: Path, model: str, sign_dev: bool = True) -> bytes:
    with open(json_file, "r") as f:
        data = json.load(f)
    file_dir = json_file.parent
    font_dir = file_dir / "fonts"
    order_json_file = file_dir / "order.json"
    return blob_from_dict(data, font_dir, order_json_file, model, sign_dev)


def blob_from_url(url: str) -> bytes:
    r = requests.get(url)
    r.raise_for_status()
    return r.content


def blob_from_dict(
    data: dict[str, t.Any],
    font_dir: Path,
    order_json_file: Path,
    model: str,
    sign_dev: bool = True,
) -> bytes:
    header: JsonHeaderData = data["header"]
    translations: JsonTranslationData = data["translations"]
    font = data["font"]
    if model not in font:
        raise ValueError(
            f"Font for model {model} not found --- use one of {list(font.keys())}"
        )
    model_font: JsonFontData = font[model]
    order_raw: dict[str, str] = json.loads(order_json_file.read_text())
    order: JsonOrderData = {int(k): v for k, v in order_raw.items()}
    blob = _blob_from_data(header, translations, model_font, font_dir, order)
    if sign_dev:
        blob = Signing(blob).perform_dev_signing()
    return blob


def _blob_from_data(
    header: JsonHeaderData,
    translations: JsonTranslationData,
    font: JsonFontData,
    font_dir: Path,
    order: JsonOrderData,
) -> bytes:
    translation_data = _create_translation_data(translations, order)
    font_data = _create_font_data(font, font_dir)

    translation_data_padded = c.Aligned(ALIGNMENT, c.GreedyBytes).build(
        translation_data.build()
    )
    data_blob = translation_data_padded + font_data.build()

    header_struct = TranslationsHeader(
        language=header["language"],
        version=_version_to_tuple(header["version"]),
        data_len=len(data_blob),
        translations_count=len(translation_data),
        fonts_offset=len(translation_data_padded),
        data_hash=sha256(data_blob).digest(),
        change_language_title=header["change_language_title"],
        change_language_prompt=header["change_language_prompt"],
    )

    header_blob = _create_header_blob(
        magic=MAGIC,
        lang=header["language"],
        version=header["version"],
        data_len=len(data_blob),
        translations_length=len(translations_blob),
        translations_num=translations_num,
        data_hash=sha256(data_blob).digest(),
        change_language_title=header["change_language_title"],
        change_language_prompt=header["change_language_prompt"],
    )
    assert len(header_blob) == HEADER_LEN, "Header should be 256 bytes long"

    final_blob = header_blob + data_blob
    assert len(final_blob) % 2 == 0, "Final blob should be aligned to 2 bytes"

    return final_blob


def _create_font_data(font: JsonFontData, font_dir: Path) -> BlobTable:
    """Example structure of the font dict:
    (The beginning number corresponds to the C representation of each font)
    {
      "1_FONT_NORMAL": "font_tthoves_regular_21_cs.json",
      "2_FONT_BOLD": "font_tthoves_bold_17_cs.json",
      "3_FONT_MONO": "font_robotomono_medium_20_cs.json",
      "4_FONT_BIG": null,
      "5_FONT_DEMIBOLD": "font_tthoves_demibold_21_cs.json"
    }
    """
    fonts = {}
    for font_name, file_name in font.items():
        if not file_name:
            continue
        file_path = font_dir / file_name
        font_num = int(font_name.split("_")[0])
        fonts[font_num] = _font_blob_from_file(file_path)

    return BlobTable.from_items(fonts)


def _font_blob_from_file(json_file: Path) -> bytes:
    json_content = json.loads(json_file.read_text())
    assert all(len(codepoint) == 1 for codepoint in json_content)
    raw_content = {
        ord(codepoint): bytes.fromhex(data) for codepoint, data in json_content.items()
    }
    table = BlobTable.from_items(raw_content).build()
    return c.Aligned(ALIGNMENT, c.GreedyBytes).build(table)


def _create_translation_data(
    translations: JsonTranslationData, order: JsonOrderData
) -> TranslationData:
    items_to_write: dict[str, str] = {}
    for section_name, section in translations.items():
        for k, v in section.items():
            name = f"{section_name}__{k}"
            items_to_write[name] = v

    sorted_order = sorted(order.items())
    sorted_items = [items_to_write[name] for _, name in sorted_order]
    return TranslationData.from_items(sorted_items)
