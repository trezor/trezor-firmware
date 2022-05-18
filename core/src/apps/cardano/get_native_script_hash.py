from trezor import messages, wire
from trezor.enums import CardanoNativeScriptHashDisplayFormat

from . import layout, native_script, seed


@seed.with_keychain
async def get_native_script_hash(
    ctx: wire.Context, msg: messages.CardanoGetNativeScriptHash, keychain: seed.Keychain
) -> messages.CardanoNativeScriptHash:
    native_script.validate_native_script(msg.script)

    script_hash = native_script.get_native_script_hash(keychain, msg.script)

    if msg.display_format != CardanoNativeScriptHashDisplayFormat.HIDE:
        await layout.show_native_script(ctx, msg.script)
        await layout.show_script_hash(ctx, script_hash, msg.display_format)

    return messages.CardanoNativeScriptHash(script_hash=script_hash)
