from trezor import wire
from trezor.messages import MessageType


def boot():
    # only enable LoadDevice in debug builds
    if __debug__:
        wire.add(MessageType.LoadDevice, __name__, "load_device")
    wire.add(MessageType.ResetDevice, __name__, "reset_device")
    wire.add(MessageType.BackupDevice, __name__, "backup_device")
    wire.add(MessageType.WipeDevice, __name__, "wipe_device")
    wire.add(MessageType.RecoveryDevice, __name__, "recovery_device")
    wire.add(MessageType.ApplySettings, __name__, "apply_settings")
    wire.add(MessageType.ApplyFlags, __name__, "apply_flags")
    wire.add(MessageType.ChangePin, __name__, "change_pin")
    wire.add(MessageType.SetU2FCounter, __name__, "set_u2f_counter")
