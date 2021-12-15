from trezor.crypto import hashlib
from trezor.enums import CardanoAddressType, CardanoNativeScriptType

from apps.cardano.helpers import (
    ADDRESS_KEY_HASH_SIZE,
    INVALID_NATIVE_SCRIPT,
    SCRIPT_HASH_SIZE,
)
from apps.common import cbor

from .helpers.paths import SCHEMA_MINT
from .helpers.utils import get_public_key_hash
from .seed import Keychain, is_multisig_path

if False:
    from typing import Any

    from trezor.messages import CardanoNativeScript

    from apps.common.cbor import CborSequence

SCRIPT_ADDRESS_TYPES = (
    CardanoAddressType.BASE_SCRIPT_KEY,
    CardanoAddressType.BASE_KEY_SCRIPT,
    CardanoAddressType.BASE_SCRIPT_SCRIPT,
    CardanoAddressType.POINTER_SCRIPT,
    CardanoAddressType.ENTERPRISE_SCRIPT,
    CardanoAddressType.REWARD_SCRIPT,
)


def validate_native_script(script: CardanoNativeScript | None) -> None:
    if not script:
        raise INVALID_NATIVE_SCRIPT

    _validate_native_script_structure(script)

    if script.type == CardanoNativeScriptType.PUB_KEY:
        if script.key_hash and script.key_path:
            raise INVALID_NATIVE_SCRIPT
        if script.key_hash:
            if len(script.key_hash) != ADDRESS_KEY_HASH_SIZE:
                raise INVALID_NATIVE_SCRIPT
        elif script.key_path:
            if not is_multisig_path(script.key_path) and not SCHEMA_MINT.match(
                script.key_path
            ):
                raise INVALID_NATIVE_SCRIPT
        else:
            raise INVALID_NATIVE_SCRIPT
    elif script.type == CardanoNativeScriptType.ALL:
        for sub_script in script.scripts:
            validate_native_script(sub_script)
    elif script.type == CardanoNativeScriptType.ANY:
        for sub_script in script.scripts:
            validate_native_script(sub_script)
    elif script.type == CardanoNativeScriptType.N_OF_K:
        if script.required_signatures_count is None:
            raise INVALID_NATIVE_SCRIPT
        if script.required_signatures_count > len(script.scripts):
            raise INVALID_NATIVE_SCRIPT
        for sub_script in script.scripts:
            validate_native_script(sub_script)
    elif script.type == CardanoNativeScriptType.INVALID_BEFORE:
        if script.invalid_before is None:
            raise INVALID_NATIVE_SCRIPT
    elif script.type == CardanoNativeScriptType.INVALID_HEREAFTER:
        if script.invalid_hereafter is None:
            raise INVALID_NATIVE_SCRIPT


def _validate_native_script_structure(script: CardanoNativeScript) -> None:
    key_hash = script.key_hash
    key_path = script.key_path
    scripts = script.scripts
    required_signatures_count = script.required_signatures_count
    invalid_before = script.invalid_before
    invalid_hereafter = script.invalid_hereafter

    fields_to_be_empty: dict[CardanoNativeScriptType, tuple[Any, ...]] = {
        CardanoNativeScriptType.PUB_KEY: (
            scripts,
            required_signatures_count,
            invalid_before,
            invalid_hereafter,
        ),
        CardanoNativeScriptType.ALL: (
            key_hash,
            key_path,
            required_signatures_count,
            invalid_before,
            invalid_hereafter,
        ),
        CardanoNativeScriptType.ANY: (
            key_hash,
            key_path,
            required_signatures_count,
            invalid_before,
            invalid_hereafter,
        ),
        CardanoNativeScriptType.N_OF_K: (
            key_hash,
            key_path,
            invalid_before,
            invalid_hereafter,
        ),
        CardanoNativeScriptType.INVALID_BEFORE: (
            key_hash,
            key_path,
            required_signatures_count,
            invalid_hereafter,
        ),
        CardanoNativeScriptType.INVALID_HEREAFTER: (
            key_hash,
            key_path,
            required_signatures_count,
            invalid_before,
        ),
    }

    if script.type not in fields_to_be_empty or any(fields_to_be_empty[script.type]):
        raise INVALID_NATIVE_SCRIPT


def get_native_script_hash(keychain: Keychain, script: CardanoNativeScript) -> bytes:
    script_cbor = cbor.encode(cborize_native_script(keychain, script))
    prefixed_script_cbor = b"\00" + script_cbor
    return hashlib.blake2b(data=prefixed_script_cbor, outlen=SCRIPT_HASH_SIZE).digest()


def cborize_native_script(
    keychain: Keychain, script: CardanoNativeScript
) -> CborSequence:
    script_content: CborSequence
    if script.type == CardanoNativeScriptType.PUB_KEY:
        if script.key_hash:
            script_content = (script.key_hash,)
        elif script.key_path:
            script_content = (get_public_key_hash(keychain, script.key_path),)
        else:
            raise INVALID_NATIVE_SCRIPT
    elif script.type == CardanoNativeScriptType.ALL:
        script_content = (
            tuple(
                cborize_native_script(keychain, sub_script)
                for sub_script in script.scripts
            ),
        )
    elif script.type == CardanoNativeScriptType.ANY:
        script_content = (
            tuple(
                cborize_native_script(keychain, sub_script)
                for sub_script in script.scripts
            ),
        )
    elif script.type == CardanoNativeScriptType.N_OF_K:
        script_content = (
            script.required_signatures_count,
            tuple(
                cborize_native_script(keychain, sub_script)
                for sub_script in script.scripts
            ),
        )
    elif script.type == CardanoNativeScriptType.INVALID_BEFORE:
        script_content = (script.invalid_before,)
    elif script.type == CardanoNativeScriptType.INVALID_HEREAFTER:
        script_content = (script.invalid_hereafter,)
    else:
        raise INVALID_NATIVE_SCRIPT

    return (script.type,) + script_content
