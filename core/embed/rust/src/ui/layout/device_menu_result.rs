use crate::micropython::{
    macros::{obj_dict, obj_map, obj_type},
    qstr::Qstr,
    simple_type::SimpleTypeObj,
    typ::Type,
};

static DEVICE_MENU_RESULT_BASE_TYPE: Type = obj_type! { name: Qstr::MP_QSTR_DeviceMenuResult, };

// Root menu
pub static BACKUP_FAILED: SimpleTypeObj = SimpleTypeObj::new(&DEVICE_MENU_RESULT_BASE_TYPE);
// Bluetooth
pub static BLUETOOTH: SimpleTypeObj = SimpleTypeObj::new(&DEVICE_MENU_RESULT_BASE_TYPE);
// "Pair & Connect"
pub static DEVICE_PAIR: SimpleTypeObj = SimpleTypeObj::new(&DEVICE_MENU_RESULT_BASE_TYPE);
pub static DEVICE_DISCONNECT: SimpleTypeObj = SimpleTypeObj::new(&DEVICE_MENU_RESULT_BASE_TYPE);
pub static DEVICE_UNPAIR: SimpleTypeObj = SimpleTypeObj::new(&DEVICE_MENU_RESULT_BASE_TYPE);
pub static DEVICE_UNPAIR_ALL: SimpleTypeObj = SimpleTypeObj::new(&DEVICE_MENU_RESULT_BASE_TYPE);
// Security menu
pub static PIN_CODE: SimpleTypeObj = SimpleTypeObj::new(&DEVICE_MENU_RESULT_BASE_TYPE);
pub static PIN_REMOVE: SimpleTypeObj = SimpleTypeObj::new(&DEVICE_MENU_RESULT_BASE_TYPE);
pub static AUTO_LOCK_DELAY: SimpleTypeObj = SimpleTypeObj::new(&DEVICE_MENU_RESULT_BASE_TYPE);
pub static WIPE_CODE: SimpleTypeObj = SimpleTypeObj::new(&DEVICE_MENU_RESULT_BASE_TYPE);
pub static WIPE_REMOVE: SimpleTypeObj = SimpleTypeObj::new(&DEVICE_MENU_RESULT_BASE_TYPE);
pub static CHECK_BACKUP: SimpleTypeObj = SimpleTypeObj::new(&DEVICE_MENU_RESULT_BASE_TYPE);
// Device menu
pub static DEVICE_NAME: SimpleTypeObj = SimpleTypeObj::new(&DEVICE_MENU_RESULT_BASE_TYPE);
pub static SCREEN_BRIGHTNESS: SimpleTypeObj = SimpleTypeObj::new(&DEVICE_MENU_RESULT_BASE_TYPE);
pub static HAPTIC_FEEDBACK: SimpleTypeObj = SimpleTypeObj::new(&DEVICE_MENU_RESULT_BASE_TYPE);
pub static LED_ENABLED: SimpleTypeObj = SimpleTypeObj::new(&DEVICE_MENU_RESULT_BASE_TYPE);
pub static WIPE_DEVICE: SimpleTypeObj = SimpleTypeObj::new(&DEVICE_MENU_RESULT_BASE_TYPE);
// Power settings
pub static TURN_OFF: SimpleTypeObj = SimpleTypeObj::new(&DEVICE_MENU_RESULT_BASE_TYPE);
pub static REBOOT: SimpleTypeObj = SimpleTypeObj::new(&DEVICE_MENU_RESULT_BASE_TYPE);
pub static REBOOT_TO_BOOTLOADER: SimpleTypeObj = SimpleTypeObj::new(&DEVICE_MENU_RESULT_BASE_TYPE);

// Create a DeviceMenuResult class that contains all result types
static DEVICE_MENU_RESULT_TYPE: Type = obj_type! {
    name: Qstr::MP_QSTR_DeviceMenuResult,
    locals: &obj_dict! { obj_map! {
        Qstr::MP_QSTR_BackupFailed => BACKUP_FAILED.as_obj(),
        Qstr::MP_QSTR_Bluetooth => BLUETOOTH.as_obj(),
        Qstr::MP_QSTR_DevicePair => DEVICE_PAIR.as_obj(),
        Qstr::MP_QSTR_DeviceDisconnect => DEVICE_DISCONNECT.as_obj(),
        Qstr::MP_QSTR_DeviceUnpair => DEVICE_UNPAIR.as_obj(),
        Qstr::MP_QSTR_DeviceUnpairAll => DEVICE_UNPAIR_ALL.as_obj(),
        Qstr::MP_QSTR_PinCode => PIN_CODE.as_obj(),
        Qstr::MP_QSTR_PinRemove => PIN_REMOVE.as_obj(),
        Qstr::MP_QSTR_AutoLockDelay => AUTO_LOCK_DELAY.as_obj(),
        Qstr::MP_QSTR_WipeCode => WIPE_CODE.as_obj(),
        Qstr::MP_QSTR_WipeRemove => WIPE_REMOVE.as_obj(),
        Qstr::MP_QSTR_CheckBackup => CHECK_BACKUP.as_obj(),
        Qstr::MP_QSTR_DeviceName => DEVICE_NAME.as_obj(),
        Qstr::MP_QSTR_ScreenBrightness => SCREEN_BRIGHTNESS.as_obj(),
        Qstr::MP_QSTR_HapticFeedback => HAPTIC_FEEDBACK.as_obj(),
        Qstr::MP_QSTR_LedEnabled => LED_ENABLED.as_obj(),
        Qstr::MP_QSTR_WipeDevice => WIPE_DEVICE.as_obj(),
        Qstr::MP_QSTR_TurnOff => TURN_OFF.as_obj(),
        Qstr::MP_QSTR_Reboot => REBOOT.as_obj(),
        Qstr::MP_QSTR_RebootToBootloader => REBOOT_TO_BOOTLOADER.as_obj(),
    } },
};

pub static DEVICE_MENU_RESULT: SimpleTypeObj = SimpleTypeObj::new(&DEVICE_MENU_RESULT_TYPE);
