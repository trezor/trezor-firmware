use crate::micropython::{
    macros::{obj_dict, obj_map, obj_type},
    qstr::Qstr,
    simple_type::SimpleTypeObj,
    typ::Type,
};

static DEVICE_MENU_RESULT_BASE_TYPE: Type = obj_type! { name: Qstr::MP_QSTR_DeviceMenuResult, };

// Root menu
pub static REVIEW_FAILED_BACKUP: SimpleTypeObj = SimpleTypeObj::new(&DEVICE_MENU_RESULT_BASE_TYPE);
pub static BACKUP_DEVICE: SimpleTypeObj = SimpleTypeObj::new(&DEVICE_MENU_RESULT_BASE_TYPE);
// "Pair & Connect"
pub static PAIR_DEVICE: SimpleTypeObj = SimpleTypeObj::new(&DEVICE_MENU_RESULT_BASE_TYPE);
pub static DISCONNECT_DEVICE: SimpleTypeObj = SimpleTypeObj::new(&DEVICE_MENU_RESULT_BASE_TYPE);
pub static UNPAIR_DEVICE: SimpleTypeObj = SimpleTypeObj::new(&DEVICE_MENU_RESULT_BASE_TYPE);
pub static UNPAIR_ALL_DEVICES: SimpleTypeObj = SimpleTypeObj::new(&DEVICE_MENU_RESULT_BASE_TYPE);
// Settings
pub static TOGGLE_BLUETOOTH: SimpleTypeObj = SimpleTypeObj::new(&DEVICE_MENU_RESULT_BASE_TYPE);

// Security menu
pub static SET_OR_CHANGE_PIN: SimpleTypeObj = SimpleTypeObj::new(&DEVICE_MENU_RESULT_BASE_TYPE);
pub static REMOVE_PIN: SimpleTypeObj = SimpleTypeObj::new(&DEVICE_MENU_RESULT_BASE_TYPE);
pub static SET_AUTO_LOCK_BATTERY: SimpleTypeObj = SimpleTypeObj::new(&DEVICE_MENU_RESULT_BASE_TYPE);
pub static SET_AUTO_LOCK_USB: SimpleTypeObj = SimpleTypeObj::new(&DEVICE_MENU_RESULT_BASE_TYPE);
pub static SET_OR_CHANGE_WIPE_CODE: SimpleTypeObj =
    SimpleTypeObj::new(&DEVICE_MENU_RESULT_BASE_TYPE);
pub static REMOVE_WIPE_CODE: SimpleTypeObj = SimpleTypeObj::new(&DEVICE_MENU_RESULT_BASE_TYPE);
pub static CHECK_BACKUP: SimpleTypeObj = SimpleTypeObj::new(&DEVICE_MENU_RESULT_BASE_TYPE);
// Device menu
pub static SET_DEVICE_NAME: SimpleTypeObj = SimpleTypeObj::new(&DEVICE_MENU_RESULT_BASE_TYPE);
pub static SET_BRIGHTNESS: SimpleTypeObj = SimpleTypeObj::new(&DEVICE_MENU_RESULT_BASE_TYPE);
pub static TOGGLE_HAPTICS: SimpleTypeObj = SimpleTypeObj::new(&DEVICE_MENU_RESULT_BASE_TYPE);
pub static TOGGLE_LED: SimpleTypeObj = SimpleTypeObj::new(&DEVICE_MENU_RESULT_BASE_TYPE);
pub static WIPE_DEVICE: SimpleTypeObj = SimpleTypeObj::new(&DEVICE_MENU_RESULT_BASE_TYPE);
// Power settings
pub static TURN_OFF: SimpleTypeObj = SimpleTypeObj::new(&DEVICE_MENU_RESULT_BASE_TYPE);
pub static REBOOT: SimpleTypeObj = SimpleTypeObj::new(&DEVICE_MENU_RESULT_BASE_TYPE);
pub static REBOOT_TO_BOOTLOADER: SimpleTypeObj = SimpleTypeObj::new(&DEVICE_MENU_RESULT_BASE_TYPE);
// Misc
pub static REFRESH_MENU: SimpleTypeObj = SimpleTypeObj::new(&DEVICE_MENU_RESULT_BASE_TYPE);

// Create a DeviceMenuResult class that contains all result types
static DEVICE_MENU_RESULT_TYPE: Type = obj_type! {
    name: Qstr::MP_QSTR_DeviceMenuResult,
    locals: &obj_dict! { obj_map! {
        Qstr::MP_QSTR_ReviewFailedBackup => REVIEW_FAILED_BACKUP.as_obj(),
        Qstr::MP_QSTR_PairDevice => PAIR_DEVICE.as_obj(),
        Qstr::MP_QSTR_DisconnectDevice => DISCONNECT_DEVICE.as_obj(),
        Qstr::MP_QSTR_UnpairDevice => UNPAIR_DEVICE.as_obj(),
        Qstr::MP_QSTR_UnpairAllDevices => UNPAIR_ALL_DEVICES.as_obj(),
        Qstr::MP_QSTR_ToggleBluetooth => TOGGLE_BLUETOOTH.as_obj(),
        Qstr::MP_QSTR_SetOrChangePin => SET_OR_CHANGE_PIN.as_obj(),
        Qstr::MP_QSTR_RemovePin => REMOVE_PIN.as_obj(),
        Qstr::MP_QSTR_SetAutoLockBattery => SET_AUTO_LOCK_BATTERY.as_obj(),
        Qstr::MP_QSTR_SetAutoLockUSB => SET_AUTO_LOCK_USB.as_obj(),
        Qstr::MP_QSTR_SetOrChangeWipeCode => SET_OR_CHANGE_WIPE_CODE.as_obj(),
        Qstr::MP_QSTR_RemoveWipeCode => REMOVE_WIPE_CODE.as_obj(),
        Qstr::MP_QSTR_CheckBackup => CHECK_BACKUP.as_obj(),
        Qstr::MP_QSTR_SetDeviceName => SET_DEVICE_NAME.as_obj(),
        Qstr::MP_QSTR_SetBrightness => SET_BRIGHTNESS.as_obj(),
        Qstr::MP_QSTR_ToggleHaptics => TOGGLE_HAPTICS.as_obj(),
        Qstr::MP_QSTR_ToggleLed => TOGGLE_LED.as_obj(),
        Qstr::MP_QSTR_WipeDevice => WIPE_DEVICE.as_obj(),
        Qstr::MP_QSTR_TurnOff => TURN_OFF.as_obj(),
        Qstr::MP_QSTR_Reboot => REBOOT.as_obj(),
        Qstr::MP_QSTR_RebootToBootloader => REBOOT_TO_BOOTLOADER.as_obj(),
        Qstr::MP_QSTR_RefreshMenu => REFRESH_MENU.as_obj(),
    } },
};

pub static DEVICE_MENU_RESULT: SimpleTypeObj = SimpleTypeObj::new(&DEVICE_MENU_RESULT_TYPE);
