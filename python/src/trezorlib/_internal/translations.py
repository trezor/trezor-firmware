from __future__ import annotations

import json
import typing as t
import unicodedata
from hashlib import sha256
from pathlib import Path

import construct as c
from construct_classes import Struct, subcon
from typing_extensions import Self, TypedDict

from ..debuglink import LayoutType
from ..firmware.models import Model
from ..models import TrezorModel
from ..tools import EnumAdapter, TupleAdapter

# All sections need to be aligned to 2 bytes for the offset tables using u16 to work properly
ALIGNMENT = 2
# "align end of struct" subcon. The builtin c.Aligned does not do the right thing,
# because it assumes that the alignment is relative to the start of the subcon, not the
# start of the whole struct.
# TODO this spelling may or may not align in context of the stream as a whole (as
# opposed to the containing struct). This is prooobably not a problem -- we want the
# top-level alignment to always be ALIGNMENT anyway. But if someone were to use some
# of the structs separately, they might get a surprise. Maybe. Didn't test this.
ALIGN_SUBCON = c.Padding(
    lambda ctx: (ALIGNMENT - (ctx._io.tell() % ALIGNMENT)) % ALIGNMENT
)

JsonFontInfo = t.Dict[str, str]
Order = t.Dict[int, str]
VersionTuple = t.Tuple[int, int, int, int]


class JsonHeader(TypedDict):
    language: str
    version: str


class JsonDef(TypedDict):
    header: JsonHeader
    translations: dict[str, str | dict[str, str]]
    fonts: dict[str, JsonFontInfo]


def version_from_json(json_str: str) -> VersionTuple:
    version_digits = [int(v) for v in json_str.split(".")]
    if len(version_digits) < 4:
        version_digits.extend([0] * (4 - len(version_digits)))
    return t.cast(VersionTuple, tuple(version_digits))


def _normalize(what: str) -> str:
    return unicodedata.normalize("NFKC", what)


def offsets_seq(data: t.Iterable[bytes]) -> t.Iterator[int]:
    offset = 0
    for item in data:
        yield offset
        offset += len(item)
    yield offset


class Header(Struct):
    language: str
    model: Model
    firmware_version: VersionTuple
    data_len: int
    data_hash: bytes

    # fmt: off
    SUBCON = c.Struct(
        "magic" / c.Const(b"TR"),
        "language" / c.PaddedString(8, "ascii"),  # BCP47 language tag
        "model" / EnumAdapter(c.Bytes(4), Model),
        "firmware_version" / TupleAdapter(c.Int8ul, c.Int8ul, c.Int8ul, c.Int8ul),
        "data_len" / c.Int16ul,
        "data_hash" / c.Bytes(32),
        ALIGN_SUBCON,
        c.Terminated,
    )
    # fmt: on


class Proof(Struct):
    merkle_proof: list[bytes]
    sigmask: int
    signature: bytes

    # fmt: off
    SUBCON = c.Struct(
        "merkle_proof" / c.PrefixedArray(c.Int8ul, c.Bytes(32)),
        "sigmask" / c.Byte,
        "signature" / c.Bytes(64),
        ALIGN_SUBCON,
        c.Terminated,
    )
    # fmt: on


class BlobTable(Struct):
    offsets: list[tuple[int, int]]
    data: bytes

    SENTINEL: t.ClassVar[int] = 0xFFFF

    # fmt: off
    SUBCON = c.Struct(
        "_length" / c.Rebuild(c.Int16ul, c.len_(c.this.offsets) - 1),
        "offsets" / c.Array(c.this._length + 1, TupleAdapter(c.Int16ul, c.Int16ul)),
        "data" / c.GreedyBytes,
        ALIGN_SUBCON,
        c.Terminated,
    )
    # fmt: on

    @classmethod
    def from_items(cls, items: dict[int, bytes]) -> Self:
        assert not any(key >= cls.SENTINEL for key in items.keys())
        keys = sorted(items.keys())
        items_sorted = [items[key] for key in keys]
        offsets = list(offsets_seq(items_sorted))
        keys.append(cls.SENTINEL)
        assert len(keys) == len(offsets)
        return cls(
            offsets=list(zip(keys, offsets)),
            data=b"".join(items_sorted),
        )

    def __len__(self) -> int:
        return len(self.offsets) - 1

    def get(self, id: int) -> bytes | None:
        if id == self.SENTINEL:
            return None
        for key, offset in self.offsets:
            if key == id:
                return self.data[offset : self.offsets[key + 1][1]]
        return None


class TranslatedStrings(Struct):
    offsets: list[int]
    strings: bytes

    # fmt: off
    SUBCON = c.Struct(
        "_length" / c.Rebuild(c.Int16ul, c.len_(c.this.offsets) - 1),
        "offsets" / c.Array(c.this._length + 1, c.Int16ul),
        "strings" / c.GreedyBytes,
        ALIGN_SUBCON,
        c.Terminated,
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


# ===========


class Font(BlobTable):
    @classmethod
    def from_file(cls, file: Path) -> Self:
        json_content = json.loads(file.read_text())
        assert all(len(codepoint) == 1 for codepoint in json_content)
        raw_content = {
            ord(codepoint): bytes.fromhex(data)
            for codepoint, data in json_content.items()
        }
        return cls.from_items(raw_content)


class FontsTable(BlobTable):
    @classmethod
    def from_dir(cls, model_fonts: dict[str, str], font_dir: Path) -> Self:
        """Example structure of the font dict:
        (The key number corresponds to the index representation of each font set in `gen_font.py`)
        {
          "1": "font_tthoves_regular_21_cs.json",
          "3": "font_robotomono_medium_20_cs.json",
          "5": "font_tthoves_demibold_21_cs.json",
          "7": "font_tthoves_bold_17_upper_cs.json"
        }
        """
        fonts = {}
        for font_name, file_name in model_fonts.items():
            if not file_name:
                continue
            file_path = font_dir / file_name
            font_num = int(font_name)
            try:
                fonts[font_num] = Font.from_file(file_path).build()
            except Exception as e:
                raise ValueError(f"Failed to load font {file_name}") from e

        return cls.from_items(fonts)

    def get_font(self, font_id: int) -> Font | None:
        font_bytes = self.get(font_id)
        if font_bytes is None:
            return None
        return Font.parse(font_bytes)


# =========


class Payload(Struct):
    translations_bytes: bytes
    fonts_bytes: bytes

    # fmt: off
    SUBCON = c.Struct(
        "translations_bytes" / c.Prefixed(c.Int16ul, c.GreedyBytes),
        "fonts_bytes" / c.Prefixed(c.Int16ul, c.GreedyBytes),
        c.Terminated,
    )
    # fmt: on


class TranslationsBlob(Struct):
    header_bytes: bytes
    proof_bytes: bytes
    payload: Payload = subcon(Payload)

    # fmt: off
    SUBCON = c.Struct(
        "magic" / c.Const(b"TRTR00"),
        "total_length" / c.Rebuild(
            c.Int16ul,
            (
                c.len_(c.this.header_bytes)
                + c.len_(c.this.proof_bytes)
                + c.len_(c.this.payload.translations_bytes)
                + c.len_(c.this.payload.fonts_bytes)
                + 2 * 4  # sizeof(u16) * number of fields
            )
        ),
        "_start_offset" / c.Tell,
        "header_bytes" / c.Prefixed(c.Int16ul, c.GreedyBytes),
        "proof_bytes" / c.Prefixed(c.Int16ul, c.GreedyBytes),
        "payload" / Payload.SUBCON,
        "_end_offset" / c.Tell,
        c.Terminated,

        c.Check(c.this.total_length == c.this._end_offset - c.this._start_offset),
    )
    # fmt: on

    @property
    def header(self):
        return Header.parse(self.header_bytes)

    @property
    def proof(self):
        return Proof.parse(self.proof_bytes)

    @proof.setter
    def proof(self, proof: Proof):
        self.proof_bytes = proof.build()

    @property
    def translations(self):
        return TranslatedStrings.parse(self.payload.translations_bytes)

    @property
    def fonts(self):
        return FontsTable.parse(self.payload.fonts_bytes)

    def build(self) -> bytes:
        assert len(self.header_bytes) % ALIGNMENT == 0
        assert len(self.proof_bytes) % ALIGNMENT == 0
        assert len(self.payload.translations_bytes) % ALIGNMENT == 0
        assert len(self.payload.fonts_bytes) % ALIGNMENT == 0
        return super().build()


# ====================

# layouts with translation support
ALL_LAYOUTS = frozenset(LayoutType) - {LayoutType.T1}
ALL_LAYOUT_NAMES = frozenset(layout.name for layout in ALL_LAYOUTS)


def check_blob(lang_data: JsonDef):
    json_header: JsonHeader = lang_data["header"]
    lang_version = f"{json_header['language']} v{json_header['version']}"

    font_layout_names = set(lang_data["fonts"].keys())
    if font_layout_names != ALL_LAYOUT_NAMES:
        raise ValueError(
            f"Invalid font layout names for {lang_version}: {font_layout_names}"
        )

    for key, item in lang_data["translations"].items():
        if isinstance(item, dict):
            item_layouts = set(item.keys())
            unknown_layouts = item_layouts - ALL_LAYOUT_NAMES
            missing_layouts = ALL_LAYOUT_NAMES - item_layouts

            if unknown_layouts or missing_layouts:
                raise ValueError(
                    f"Invalid translation layouts for {lang_version}: {key}"
                    f"\nUnknown layouts: {list(unknown_layouts)}"
                    f"\nMissing layouts: {list(missing_layouts)}"
                )


def order_from_json(json_order: dict[str, str]) -> Order:
    return {int(k): v for k, v in json_order.items()}


def get_translation(lang_data: JsonDef, key: str, layout_type: LayoutType) -> str:
    item = lang_data["translations"].get(key, "")
    if isinstance(item, dict):
        return item.get(layout_type.name, "")

    return item  # Same translation for all layouts


def blob_from_defs(
    lang_data: JsonDef,
    order: Order,
    model: TrezorModel,
    version: VersionTuple,
    fonts_dir: Path,
) -> TranslationsBlob:
    json_header: JsonHeader = lang_data["header"]
    layout_type = LayoutType.from_model(model)

    # order translations -- python dicts keep insertion order
    translations_ordered: list[str] = [
        get_translation(lang_data, key, layout_type) for _, key in sorted(order.items())
    ]

    translations = TranslatedStrings.from_items(translations_ordered)

    if layout_type.name not in lang_data["fonts"]:
        raise ValueError(
            f"Layout {layout_type.name} not found in header for {json_header['language']} v{json_header['version']}"
        )

    model_fonts = lang_data["fonts"][layout_type.name]
    fonts = FontsTable.from_dir(model_fonts, fonts_dir)

    translations_bytes = translations.build()
    assert len(translations_bytes) % ALIGNMENT == 0
    fonts_bytes = fonts.build()
    assert len(fonts_bytes) % ALIGNMENT == 0

    payload = Payload(
        translations_bytes=translations_bytes,
        fonts_bytes=fonts_bytes,
    )
    data = payload.build()

    header = Header(
        language=json_header["language"],
        model=Model.from_trezor_model(model),
        firmware_version=version,
        data_len=len(data),
        data_hash=sha256(data).digest(),
    )

    return TranslationsBlob(
        header_bytes=header.build(),
        proof_bytes=b"",
        payload=payload,
    )
