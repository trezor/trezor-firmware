from trezor import wire
from trezor.enums import CardanoNativeScriptHashDisplayFormat
from trezor.messages import CardanoNativeScriptHash

from . import native_script, seed
from .layout import show_native_script, show_script_hash

if False:
    from trezor.messages import CardanoGetNativeScriptHash


@seed.with_keychain
async def get_native_script_hash(
    ctx: wire.Context, msg: CardanoGetNativeScriptHash, keychain: seed.Keychain
) -> CardanoNativeScriptHash:
    native_script.validate_native_script(msg.script)

    script_hash = native_script.get_native_script_hash(keychain, msg.script)

    if msg.display_format != CardanoNativeScriptHashDisplayFormat.HIDE:
        await show_native_script(ctx, msg.script)
        await show_script_hash(ctx, script_hash, msg.display_format)

    return CardanoNativeScriptHash(script_hash=script_hash)
