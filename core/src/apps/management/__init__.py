from trezor import wire
from trezor.messages import MessageType


def boot() -> None:
    wire.add(MessageType.ResetDevice, __name__, "reset_device")
    wire.add(MessageType.BackupDevice, __name__, "backup_device")
    wire.add(MessageType.WipeDevice, __name__, "wipe_device")
    wire.add(MessageType.RecoveryDevice, __name__, "recovery_device")
    wire.add(MessageType.ApplySettings, __name__, "apply_settings")
    wire.add(MessageType.ApplyFlags, __name__, "apply_flags")
    wire.add(MessageType.ChangePin, __name__, "change_pin")
    wire.add(MessageType.SetU2FCounter, __name__, "set_u2f_counter")
    wire.add(MessageType.GetNextU2FCounter, __name__, "get_next_u2f_counter")
    wire.add(MessageType.SdProtect, __name__, "sd_protect")
    wire.add(MessageType.ChangeWipeCode, __name__, "change_wipe_code")
