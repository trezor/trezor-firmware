from micropython import const

import storage.device
from trezor import io
from trezor.crypto import hmac
from trezor.crypto.hashlib import sha256
from trezor.utils import consteq

if False:
    from typing import Optional

SD_CARD_HOT_SWAPPABLE = False
SD_SALT_LEN_BYTES = const(32)
SD_SALT_AUTH_TAG_LEN_BYTES = const(16)


class SdSaltMismatch(Exception):
    pass


def is_enabled() -> bool:
    return storage.device.get_sd_salt_auth_key() is not None


def compute_auth_tag(salt: bytes, auth_key: bytes) -> bytes:
    digest = hmac.new(auth_key, salt, sha256).digest()
    return digest[:SD_SALT_AUTH_TAG_LEN_BYTES]


def _get_device_dir() -> str:
    return "/trezor/device_{}".format(storage.device.get_device_id().lower())


def _get_salt_path(new: bool = False) -> str:
    return "{}/salt{}".format(_get_device_dir(), ".new" if new else "")


def _load_salt(fs: io.FatFS, auth_key: bytes, path: str) -> Optional[bytearray]:
    # Load the salt file if it exists.
    try:
        with fs.open(path, "r") as f:
            salt = bytearray(SD_SALT_LEN_BYTES)
            stored_tag = bytearray(SD_SALT_AUTH_TAG_LEN_BYTES)
            f.read(salt)
            f.read(stored_tag)
    except OSError:
        return None

    # Check the salt's authentication tag.
    computed_tag = compute_auth_tag(salt, auth_key)
    if not consteq(computed_tag, stored_tag):
        return None

    return salt


def load_sd_salt() -> Optional[bytearray]:
    salt_auth_key = storage.device.get_sd_salt_auth_key()
    if salt_auth_key is None:
        return None

    sd = io.SDCard()
    if not sd.power(True):
        raise OSError

    salt_path = _get_salt_path()
    new_salt_path = _get_salt_path(new=True)

    try:
        fs = io.FatFS()
        try:
            fs.mount()
        except OSError as e:
            # SD card is probably not formatted. For purposes of loading SD salt, this
            # is identical to having the wrong card in.
            raise SdSaltMismatch from e

        salt = _load_salt(fs, salt_auth_key, salt_path)
        if salt is not None:
            return salt

        # Check if there is a new salt.
        salt = _load_salt(fs, salt_auth_key, new_salt_path)
        if salt is None:
            # No valid salt file on this SD card.
            raise SdSaltMismatch

        # Normal salt file does not exist, but new salt file exists. That means that
        # SD salt regeneration was interrupted earlier. Bring into consistent state.
        # TODO Possibly overwrite salt file with random data.
        try:
            fs.unlink(salt_path)
        except OSError:
            pass

        # fs.rename can fail with a write error, which falls through as an OSError.
        # This should be handled in calling code, by allowing the user to retry.
        fs.rename(new_salt_path, salt_path)
        return salt
    finally:
        fs.unmount()
        sd.power(False)


def set_sd_salt(salt: bytes, salt_tag: bytes, stage: bool = False) -> None:
    salt_path = _get_salt_path(stage)
    sd = io.SDCard()
    if not sd.power(True):
        raise OSError

    try:
        fs = io.FatFS()
        fs.mount()
        fs.mkdir("/trezor", True)
        fs.mkdir(_get_device_dir(), True)
        with fs.open(salt_path, "w") as f:
            f.write(salt)
            f.write(salt_tag)
    finally:
        fs.unmount()
        sd.power(False)


def commit_sd_salt() -> None:
    salt_path = _get_salt_path(new=False)
    new_salt_path = _get_salt_path(new=True)

    sd = io.SDCard()
    fs = io.FatFS()
    if not sd.power(True):
        raise OSError

    try:
        fs.mount()
        # TODO Possibly overwrite salt file with random data.
        try:
            fs.unlink(salt_path)
        except OSError:
            pass
        fs.rename(new_salt_path, salt_path)
    finally:
        fs.unmount()
        sd.power(False)


def remove_sd_salt() -> None:
    salt_path = _get_salt_path()

    sd = io.SDCard()
    fs = io.FatFS()
    if not sd.power(True):
        raise OSError

    try:
        fs.mount()
        # TODO Possibly overwrite salt file with random data.
        fs.unlink(salt_path)
    finally:
        fs.unmount()
        sd.power(False)
