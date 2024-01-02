import json
import struct
from hashlib import sha256
from pathlib import Path
from typing import Any, Dict, List, Tuple

import requests
from typing_extensions import TypedDict

from .translations_dev_sign import sign_with_dev_keys

MAGIC = b"TRTR"
# All sections need to be aligned to 2 bytes for the offset tables using u16 to work properly
ALIGNMENT_BYTE = b"\x00"
HEADER_LEN = 256
SIG_LEN = 65
# TODO: why is the sigmask used/useful?
SIGMASK = (0b111).to_bytes(1, "little")

TranslationData = Dict[str, Dict[str, str]]
HeaderData = Dict[str, str]
FontData = Dict[str, str]
OrderData = Dict[int, str]


class FileInfo(TypedDict):
    language: str
    version: str
    supported_models: List[str]


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
    header: HeaderData = data["header"]
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
    data: Dict[str, Any],
    font_dir: Path,
    order_json_file: Path,
    model: str,
    sign_dev: bool = True,
) -> bytes:
    header: HeaderData = data["header"]
    translations: TranslationData = data["translations"]
    font = data["font"]
    if model not in font:
        raise ValueError(
            f"Font for model {model} not found --- use one of {list(font.keys())}"
        )
    model_font: FontData = font[model]
    order_raw: Dict[str, str] = json.loads(order_json_file.read_text())
    order: OrderData = {int(k): v for k, v in order_raw.items()}
    blob = _blob_from_data(header, translations, model_font, font_dir, order)
    if sign_dev:
        blob = Signing(blob).perform_dev_signing()
    return blob


def _blob_from_data(
    header: HeaderData,
    translations: TranslationData,
    font: FontData,
    font_dir: Path,
    order: OrderData,
) -> bytes:
    translations_blob, translations_num = _create_translations_blob(translations, order)
    assert (
        len(translations_blob) % 2 == 0
    ), "Translations data should be aligned to 2 bytes"

    font_blob = _create_font_blob(font, font_dir)
    assert len(font_blob) % 2 == 0, "Font data should be aligned to 2 bytes"

    data_blob = translations_blob + font_blob
    assert len(data_blob) % 2 == 0, "Data should be aligned to 2 bytes"

    header_blob = _create_header_blob(
        magic=MAGIC,
        lang=header["language"],
        version=header["version"],
        data_length=len(data_blob),
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


def _create_font_blob(font: FontData, font_dir: Path) -> bytearray:
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
    num_fonts: list[tuple[int, Path]] = []
    for font_name, file_name in font.items():
        if not file_name:
            continue
        file_path = font_dir / file_name
        font_num = int(font_name.split("_")[0])
        num_fonts.append((font_num, file_path))

    data_length = len(num_fonts)

    blob = bytearray()

    # Data length (2 bytes)
    blob += struct.pack("H", data_length)

    # Initialize Index Table
    # Each item has 2 bytes for font_num + 2 bytes for offset
    index_table_pos = len(blob)
    index_table_item_size = 2 + 2
    blob.extend(bytearray(index_table_item_size * data_length))

    # Append specific fonts and fill Index Table
    offset = len(blob)
    for font_num, file_path in sorted(num_fonts):
        # Looks like pyright bug below
        specific_font_data = _font_blob_from_file(file_path)  # type: ignore [Argument of type "int" cannot be assigned to parameter "json_file"]

        assert (
            len(specific_font_data) % 2 == 0
        ), "Specific font data should be aligned to 2 bytes"

        # Update index table
        struct.pack_into("HH", blob, index_table_pos, font_num, offset)

        # Append character data
        blob.extend(specific_font_data)

        # Update offset and index_table_pos
        offset += len(specific_font_data)
        index_table_pos += index_table_item_size

    return blob


def _font_blob_from_file(json_file: Path) -> bytearray:
    json_content = json.loads(json_file.read_text())
    data_length = len(json_content)

    blob = bytearray()

    # Data length (2 bytes)
    blob += struct.pack("H", data_length)

    # Initialize Index Table
    # Each item has 2 bytes for char_code + 2 bytes for offset
    index_table_pos = len(blob)
    index_table_item_size = 2 + 2
    blob.extend(bytearray(index_table_item_size * data_length))

    # Append Character Data and fill Index Table
    offset = len(blob)
    for obj in json_content:
        utf8_char_str = obj["utf8"]
        assert len(utf8_char_str) == 4
        char_code = int(utf8_char_str, 16)
        data = bytes.fromhex(obj["data"])

        # Update index table
        struct.pack_into("HH", blob, index_table_pos, char_code, offset)

        # Append character data
        blob.extend(data)

        # Update offset and index_table_pos
        offset += len(data)
        index_table_pos += index_table_item_size

    if len(blob) % 2 == 1:
        blob += ALIGNMENT_BYTE

    return blob


def _create_translations_blob(
    translations: TranslationData, order: OrderData
) -> Tuple[bytearray, int]:
    items_to_write: Dict[str, str] = {}
    for section_name, section in translations.items():
        for k, v in section.items():
            name = f"{section_name}__{k}"
            items_to_write[name] = v

    data_length = len(order)

    blob = bytearray()

    # Initialize Index Table
    # Each item has 2 bytes for offset
    index_table_pos = len(blob)
    index_table_item_size = 2
    blob.extend(bytearray(index_table_item_size * data_length))

    sorted_order = sorted(order.items(), key=lambda x: x[0])

    # Append Translation Data and fill Index Table
    offset = len(blob)
    for _, name in sorted_order:
        # Update index table
        struct.pack_into("H", blob, index_table_pos, offset)

        # Append translation data
        # Value might not be there, as the string may have been deleted in the past
        value = items_to_write.get(name)
        if value:
            data = value.encode()
            blob.extend(data)
            offset += len(data)

        index_table_pos += index_table_item_size

    if len(blob) % 2 == 1:
        blob += ALIGNMENT_BYTE

    return blob, data_length


def _create_header_blob(
    magic: bytes,
    lang: str,
    version: str,
    data_length: int,
    translations_length: int,
    translations_num: int,
    data_hash: bytes,
    change_language_title: str,
    change_language_prompt: str,
) -> bytes:
    header = b""

    # Magic (4 bytes)
    assert len(magic) == 4, "Magic should be 4 bytes long"
    header += struct.pack("4s", magic)

    # Version (16 bytes)
    assert len(version.encode()) <= 16, "Version string is too long"
    header += struct.pack("16s", version.encode())

    # Language name (32 bytes)
    assert len(lang.encode()) <= 32, "Language name is too long"
    header += struct.pack("32s", lang.encode())

    # Data length (2 bytes)
    assert 0 <= data_length <= 0xFFFF, "Data length should fit in two bytes"
    header += struct.pack("H", data_length)

    # Translations length (2 bytes)
    assert (
        0 <= translations_length <= 0xFFFF
    ), "Translations length should fit in two bytes"
    header += struct.pack("H", translations_length)

    # Translations amount (2 bytes)
    assert 0 <= translations_num <= 0xFFFF, "Translation num should fit in two bytes"
    header += struct.pack("H", translations_num)

    # Data hash (32 bytes)
    assert len(data_hash) == 32, "Data hash should be 32 bytes long"
    header += struct.pack("32s", data_hash)

    # Change language title (20 bytes)
    # Needs to be ASCII because it will be shown with english ASCII-only fonts
    assert change_language_title.isascii(), "Change language title should be ascii"  # type: ignore [Cannot access member "isascii"]
    assert (
        len(change_language_title.encode()) <= 20
    ), "Change language title is too long"
    header += struct.pack("20s", change_language_title.encode())

    # Change language prompt (40 bytes)
    # Needs to be ASCII because it will be shown with english ASCII-only fonts
    assert change_language_prompt.isascii(), "Change language prompt should be ascii"  # type: ignore [Cannot access member "isascii"]
    assert (
        len(change_language_prompt.encode()) <= 40
    ), "Change language prompt is too long"
    header += struct.pack("40s", change_language_prompt.encode())

    assert (
        len(header) <= HEADER_LEN - SIG_LEN
    ), "Not enough space for signature in header"

    # Fill rest with zeros
    while not len(header) == HEADER_LEN:
        header += struct.pack("B", 0)

    return header
