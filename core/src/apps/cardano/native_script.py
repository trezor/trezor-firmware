from typing import TYPE_CHECKING

from trezor.enums import CardanoNativeScriptType
from trezor.wire import ProcessError

if TYPE_CHECKING:
    from typing import Any

    from trezor import messages

    from apps.common.cbor import CborSequence

    from . import seed


def validate_native_script(script: messages.CardanoNativeScript | None) -> None:
    from . import seed
    from .helpers import ADDRESS_KEY_HASH_SIZE
    from .helpers.paths import SCHEMA_MINT

    INVALID_NATIVE_SCRIPT = ProcessError("Invalid native script")

    if not script:
        raise INVALID_NATIVE_SCRIPT

    _validate_native_script_structure(script)
    script_type = script.type  # local_cache_attribute
    key_path = script.key_path  # local_cache_attribute
    scripts = script.scripts  # local_cache_attribute
    CNST = CardanoNativeScriptType  # local_cache_global

    if script_type == CNST.PUB_KEY:
        if script.key_hash and key_path:
            raise INVALID_NATIVE_SCRIPT
        if script.key_hash:
            if len(script.key_hash) != ADDRESS_KEY_HASH_SIZE:
                raise INVALID_NATIVE_SCRIPT
        elif key_path:
            is_minting = SCHEMA_MINT.match(key_path)
            if not seed.is_multisig_path(key_path) and not is_minting:
                raise INVALID_NATIVE_SCRIPT
        else:
            raise INVALID_NATIVE_SCRIPT
    elif script_type == CNST.ALL:
        for sub_script in scripts:
            validate_native_script(sub_script)
    elif script_type == CNST.ANY:
        for sub_script in scripts:
            validate_native_script(sub_script)
    elif script_type == CNST.N_OF_K:
        if script.required_signatures_count is None:
            raise INVALID_NATIVE_SCRIPT
        if script.required_signatures_count > len(scripts):
            raise INVALID_NATIVE_SCRIPT
        for sub_script in scripts:
            validate_native_script(sub_script)
    elif script_type == CNST.INVALID_BEFORE:
        if script.invalid_before is None:
            raise INVALID_NATIVE_SCRIPT
    elif script_type == CNST.INVALID_HEREAFTER:
        if script.invalid_hereafter is None:
            raise INVALID_NATIVE_SCRIPT


def _validate_native_script_structure(script: messages.CardanoNativeScript) -> None:
    key_hash = script.key_hash  # local_cache_attribute
    key_path = script.key_path  # local_cache_attribute
    scripts = script.scripts  # local_cache_attribute
    required_signatures_count = (
        script.required_signatures_count
    )  # local_cache_attribute
    invalid_before = script.invalid_before  # local_cache_attribute
    invalid_hereafter = script.invalid_hereafter  # local_cache_attribute
    CNST = CardanoNativeScriptType  # local_cache_global

    fields_to_be_empty: dict[CNST, tuple[Any, ...]] = {
        CNST.PUB_KEY: (
            scripts,
            required_signatures_count,
            invalid_before,
            invalid_hereafter,
        ),
        CNST.ALL: (
            key_hash,
            key_path,
            required_signatures_count,
            invalid_before,
            invalid_hereafter,
        ),
        CNST.ANY: (
            key_hash,
            key_path,
            required_signatures_count,
            invalid_before,
            invalid_hereafter,
        ),
        CNST.N_OF_K: (
            key_hash,
            key_path,
            invalid_before,
            invalid_hereafter,
        ),
        CNST.INVALID_BEFORE: (
            key_hash,
            key_path,
            required_signatures_count,
            invalid_hereafter,
        ),
        CNST.INVALID_HEREAFTER: (
            key_hash,
            key_path,
            required_signatures_count,
            invalid_before,
        ),
    }

    if script.type not in fields_to_be_empty or any(fields_to_be_empty[script.type]):
        raise ProcessError("Invalid native script")


def get_native_script_hash(
    keychain: seed.Keychain, script: messages.CardanoNativeScript
) -> bytes:
    from trezor.crypto import hashlib

    from apps.common import cbor

    from .helpers import SCRIPT_HASH_SIZE

    script_cbor = cbor.encode(cborize_native_script(keychain, script))
    prefixed_script_cbor = b"\00" + script_cbor
    return hashlib.blake2b(data=prefixed_script_cbor, outlen=SCRIPT_HASH_SIZE).digest()


def cborize_native_script(
    keychain: seed.Keychain, script: messages.CardanoNativeScript
) -> CborSequence:
    from .helpers.utils import get_public_key_hash

    script_type = script.type  # local_cache_attribute
    CNST = CardanoNativeScriptType  # local_cache_global

    script_content: CborSequence
    if script_type == CNST.PUB_KEY:
        if script.key_hash:
            script_content = (script.key_hash,)
        elif script.key_path:
            script_content = (get_public_key_hash(keychain, script.key_path),)
        else:
            raise ProcessError("Invalid native script")
    elif script_type == CNST.ALL:
        script_content = (
            tuple(
                cborize_native_script(keychain, sub_script)
                for sub_script in script.scripts
            ),
        )
    elif script_type == CNST.ANY:
        script_content = (
            tuple(
                cborize_native_script(keychain, sub_script)
                for sub_script in script.scripts
            ),
        )
    elif script_type == CNST.N_OF_K:
        script_content = (
            script.required_signatures_count,
            tuple(
                cborize_native_script(keychain, sub_script)
                for sub_script in script.scripts
            ),
        )
    elif script_type == CNST.INVALID_BEFORE:
        script_content = (script.invalid_before,)
    elif script_type == CNST.INVALID_HEREAFTER:
        script_content = (script.invalid_hereafter,)
    else:
        raise RuntimeError  # should be unreachable

    return (script_type,) + script_content
