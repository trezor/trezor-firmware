from typing import TYPE_CHECKING

from . import seed

if TYPE_CHECKING:
    from trezor.messages import CardanoGetNativeScriptHash, CardanoNativeScriptHash
    from trezor.wire import Context


@seed.with_keychain
async def get_native_script_hash(
    ctx: Context, msg: CardanoGetNativeScriptHash, keychain: seed.Keychain
) -> CardanoNativeScriptHash:
    from trezor.enums import CardanoNativeScriptHashDisplayFormat
    from trezor.messages import CardanoNativeScriptHash

    from . import layout, native_script

    native_script.validate_native_script(msg.script)

    script_hash = native_script.get_native_script_hash(keychain, msg.script)

    if msg.display_format != CardanoNativeScriptHashDisplayFormat.HIDE:
        await layout.show_native_script(ctx, msg.script)
        await layout.show_script_hash(ctx, script_hash, msg.display_format)

    return CardanoNativeScriptHash(script_hash=script_hash)
