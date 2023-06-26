from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import BackupDevice, Success


async def backup_device(msg: BackupDevice) -> Success:
    import storage.device as storage_device
    from trezor import wire
    from trezor.messages import Success

    from apps.common import mnemonic

    from .reset_device import backup_seed, layout

    if not storage_device.is_initialized():
        raise wire.NotInitialized("Device is not initialized")
    if not storage_device.needs_backup():
        raise wire.ProcessError("Seed already backed up")

    mnemonic_secret, mnemonic_type = mnemonic.get()
    if mnemonic_secret is None:
        raise RuntimeError

    storage_device.set_unfinished_backup(True)
    storage_device.set_backed_up()

    await backup_seed(mnemonic_type, mnemonic_secret)

    storage_device.set_unfinished_backup(False)

    await layout.show_backup_success()

    return Success(message="Seed successfully backed up")
