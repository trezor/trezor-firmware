from micropython import const
from typing import TYPE_CHECKING

from trezor.crypto.hashlib import sha256
from trezor.wire import DataError

if TYPE_CHECKING:
    from trezor.messages import ChangeLanguage, Success

_CHUNK_SIZE = const(1024)
_HEADER_SIZE = const(256)
_FILL_BYTE = b"\x00"


THRESHOLD = 2
PUBLIC_KEYS = (
    b"\x43\x34\x99\x63\x43\x62\x3e\x46\x2f\x0f\xc9\x33\x11\xfe\xf1\x48\x4c\xa2\x3d\x2f\xf1\xee\xc6\xdf\x1f\xa8\xeb\x7e\x35\x73\xb3\xdb",
    b"\xa9\xa2\x2c\xc2\x65\xa0\xcb\x1d\x6c\xb3\x29\xbc\x0e\x60\xbc\x45\xdf\x76\xb9\xab\x28\xfb\x87\xb6\x11\x36\xfe\xaf\x8d\x8f\xdc\x96",
    b"\xb8\xd2\xb2\x1d\xe2\x71\x24\xf0\x51\x1f\x90\x3a\xe7\xe6\x0e\x07\x96\x18\x10\xa0\xb8\xf2\x8e\xa7\x55\xfa\x50\x36\x7a\x8a\x2b\x8b",
)

if __debug__:
    DEV_PUBLIC_KEYS = (
        b"\x68\x46\x0e\xbe\xf3\xb1\x38\x16\x4e\xc7\xfd\x86\x10\xe9\x58\x00\xdf\x75\x98\xf7\x0f\x2f\x2e\xa7\xdb\x51\x72\xac\x74\xeb\xc1\x44",
        b"\x8d\x4a\xbe\x07\x4f\xef\x92\x29\xd3\xb4\x41\xdf\xea\x4f\x98\xf8\x05\xb1\xa2\xb3\xa0\x6a\xe6\x45\x81\x0e\xfe\xce\x77\xfd\x50\x44",
        b"\x97\xf7\x13\x5a\x9a\x26\x90\xe7\x3b\xeb\x26\x55\x6f\x1c\xb1\x63\xbe\xa2\x53\x2a\xff\xa1\xe7\x78\x24\x30\xbe\x98\xc0\xe5\x68\x12",
    )


class TranslationsHeader:
    MAGIC = b"TRTR"
    VERSION_LEN = 16
    LANG_LEN = 32
    DATA_HASH_LEN = 32
    CHANGE_LANGUAGE_TITLE_LEN = 20
    CHANGE_LANGUAGE_PROMPT_LEN = 40
    SIGNATURE_LEN = 64 + 1

    def __init__(
        self,
        raw_data: bytes,
        version: str,
        language: str,
        data_length: int,
        translations_length: int,
        translations_num: int,
        data_hash: bytes,
        change_language_title: str,
        change_language_prompt: str,
        sigmask: int,
        signature: bytes,
    ):
        self.raw_data = raw_data
        self.version = version
        self.language = language
        self.data_length = data_length
        self.translations_length = translations_length
        self.translations_num = translations_num
        self.data_hash = data_hash
        self.change_language_title = change_language_title
        self.change_language_prompt = change_language_prompt
        self.sigmask = sigmask
        self.signature = signature

    @classmethod
    def from_bytes(cls, data: bytes) -> "TranslationsHeader":
        from trezor.utils import BufferReader

        from apps.common import readers

        if len(data) != _HEADER_SIZE:
            raise DataError("Invalid header length")

        try:
            r = BufferReader(data)

            magic = r.read(len(cls.MAGIC))
            if magic != cls.MAGIC:
                raise DataError("Invalid header magic")

            version = r.read(cls.VERSION_LEN).rstrip(_FILL_BYTE).decode()
            language = r.read(cls.LANG_LEN).rstrip(_FILL_BYTE).decode()
            data_length = readers.read_uint16_le(r)
            translations_length = readers.read_uint16_le(r)
            translations_num = readers.read_uint16_le(r)
            data_hash = r.read(cls.DATA_HASH_LEN)
            change_language_title = (
                r.read(cls.CHANGE_LANGUAGE_TITLE_LEN).rstrip(_FILL_BYTE).decode()
            )
            change_language_prompt = (
                r.read(cls.CHANGE_LANGUAGE_PROMPT_LEN).rstrip(_FILL_BYTE).decode()
            )

            # Signature occupies last 65 bytes (sigmask + signature itself)
            rest = r.read()
            if len(rest) < cls.SIGNATURE_LEN:
                raise DataError("Invalid header data")

            zeros = rest[: -cls.SIGNATURE_LEN]
            signature_part = rest[-cls.SIGNATURE_LEN :]

            sigmask = signature_part[0]
            signature = signature_part[1:]

            # Rest must be empty bytes
            for b in zeros:
                if b != 0:
                    raise DataError("Invalid header data")

            return cls(
                raw_data=data,
                language=language,
                version=version,
                data_length=data_length,
                translations_length=translations_length,
                translations_num=translations_num,
                data_hash=data_hash,
                change_language_title=change_language_title,
                change_language_prompt=change_language_prompt,
                sigmask=sigmask,
                signature=signature,
            )
        except EOFError:
            raise DataError("Invalid header data")

    def version_tuple(self) -> tuple[int, int, int]:
        try:
            version_parts = self.version.split(".")
            major = int(version_parts[0])
            minor = int(version_parts[1])
            patch = int(version_parts[2])
            return major, minor, patch
        except (ValueError, IndexError):
            raise DataError("Invalid header version")

    def check_signature(self) -> bool:
        from trezor.crypto.cosi import verify as cosi_verify

        # Nullifying the signature data themselves
        value_to_hash = (
            self.raw_data[: -self.SIGNATURE_LEN] + b"\x00" * self.SIGNATURE_LEN
        )
        hasher = sha256()
        hasher.update(value_to_hash)
        hash: bytes = hasher.digest()
        sig_result = cosi_verify(
            self.signature, hash, THRESHOLD, PUBLIC_KEYS, self.sigmask
        )
        if __debug__:
            debug_sig_result = cosi_verify(
                self.signature, hash, THRESHOLD, DEV_PUBLIC_KEYS, self.sigmask
            )
            sig_result = sig_result or debug_sig_result
        return sig_result


async def change_language(msg: ChangeLanguage) -> Success:
    from trezor import translations, utils
    from trezor.messages import Success
    from trezor.ui.layouts.progress import progress

    data_length = msg.data_length  # local_cache_attribute

    # When empty data, reverting the language to default (english)
    if data_length == 0:
        await _require_confirm_change_language(
            "Change language", "Do you want to change language to English?"
        )
        translations.wipe()
        return Success(message="Language reverted to default")

    if data_length > translations.data_max_size():
        raise DataError("Translations too long")
    if data_length < _HEADER_SIZE:
        raise DataError("Translations too short")

    # Getting and parsing the header
    header_data = await get_data_chunk(_HEADER_SIZE, 0)
    header = TranslationsHeader.from_bytes(header_data[:])

    # Verifying header information
    if header.data_length + _HEADER_SIZE != data_length:
        raise DataError("Invalid header data length")
    # TODO: how to handle the version updates - numbers have to be bumped in cs.json and others
    # (or have this logic in a separate blob-creating tool)
    # (have some static check in make gen_check?)
    if header.version_tuple() != (
        utils.VERSION_MAJOR,
        utils.VERSION_MINOR,
        utils.VERSION_PATCH,
    ):
        raise DataError("Invalid translations version")

    # Verify signature
    if not header.check_signature():
        raise DataError("Invalid translations signature")

    # Confirm with user
    await _require_confirm_change_language(
        header.change_language_title, header.change_language_prompt
    )

    # Show indeterminate loader
    progress(None, None, True)

    # Loading all the data at once, so we can verify its fingerprint
    # If we saved it gradually to the storage and only checked the fingerprint at the end
    # (with the idea of deleting the data if the fingerprint does not match),
    # attackers could still write some data into storage and then unplug the device.
    blob = utils.empty_bytearray(translations.data_max_size())

    # Write the header
    blob.extend(header_data)

    # Requesting the data in chunks and storing them in the blob
    # Also checking the hash of the data for consistency
    data_left = data_length - len(header_data)
    offset = len(header_data)
    hash_writer = utils.HashWriter(sha256())
    while data_left > 0:
        data_chunk = await get_data_chunk(data_left, offset)
        blob.extend(data_chunk)
        hash_writer.write(data_chunk)
        data_left -= len(data_chunk)
        offset += len(data_chunk)

    # When the data do not match the hash, do not write anything
    if hash_writer.get_digest() != header.data_hash:
        raise DataError("Invalid data hash")

    translations.wipe()
    translations.write(blob, 0)

    return Success(message="Language changed")


async def get_data_chunk(data_left: int, offset: int) -> bytes:
    from trezor.messages import TranslationDataAck, TranslationDataRequest
    from trezor.wire.context import call

    data_length = min(data_left, _CHUNK_SIZE)
    req = TranslationDataRequest(data_length=data_length, data_offset=offset)
    res = await call(req, TranslationDataAck)
    return res.data_chunk


async def _require_confirm_change_language(title: str, description: str) -> None:
    from trezor.enums import ButtonRequestType
    from trezor.ui.layouts import confirm_action

    await confirm_action(
        "set_language",
        title,
        description=description,
        verb="OK",  # going for an international word, so it does not need translations
        br_code=ButtonRequestType.ProtectCall,
    )
