use crate::micropython::{
    macros::{obj_dict, obj_map, obj_type},
    qstr::Qstr,
    simple_type::SimpleTypeObj,
    typ::Type,
};

static DEVICE_MENU_RESULT_BASE_TYPE: Type = obj_type! { name: Qstr::MP_QSTR_DeviceMenuResult, };

pub static BACKUP_FAILED: SimpleTypeObj = SimpleTypeObj::new(&DEVICE_MENU_RESULT_BASE_TYPE);
pub static DEVICE_PAIR: SimpleTypeObj = SimpleTypeObj::new(&DEVICE_MENU_RESULT_BASE_TYPE);
pub static DEVICE_DISCONNECT: SimpleTypeObj = SimpleTypeObj::new(&DEVICE_MENU_RESULT_BASE_TYPE);
pub static CHECK_BACKUP: SimpleTypeObj = SimpleTypeObj::new(&DEVICE_MENU_RESULT_BASE_TYPE);
pub static WIPE_DEVICE: SimpleTypeObj = SimpleTypeObj::new(&DEVICE_MENU_RESULT_BASE_TYPE);
pub static SCREEN_BRIGHTNESS: SimpleTypeObj = SimpleTypeObj::new(&DEVICE_MENU_RESULT_BASE_TYPE);
pub static AUTO_LOCK_DELAY: SimpleTypeObj = SimpleTypeObj::new(&DEVICE_MENU_RESULT_BASE_TYPE);

pub static DEMO_CREATE_WALLET: SimpleTypeObj = SimpleTypeObj::new(&DEVICE_MENU_RESULT_BASE_TYPE);
pub static DEMO_RESTORE_WALLET: SimpleTypeObj = SimpleTypeObj::new(&DEVICE_MENU_RESULT_BASE_TYPE);
pub static DEMO_RECEIVE_BITCOIN: SimpleTypeObj = SimpleTypeObj::new(&DEVICE_MENU_RESULT_BASE_TYPE);
pub static DEMO_SEND_BITCOIN: SimpleTypeObj = SimpleTypeObj::new(&DEVICE_MENU_RESULT_BASE_TYPE);

// Create a DeviceMenuResult class that contains all result types
static DEVICE_MENU_RESULT_TYPE: Type = obj_type! {
    name: Qstr::MP_QSTR_DeviceMenuResult,
    locals: &obj_dict! { obj_map! {
        Qstr::MP_QSTR_BackupFailed => BACKUP_FAILED.as_obj(),
        Qstr::MP_QSTR_DevicePair => DEVICE_PAIR.as_obj(),
        Qstr::MP_QSTR_DeviceDisconnect => DEVICE_DISCONNECT.as_obj(),
        Qstr::MP_QSTR_CheckBackup => CHECK_BACKUP.as_obj(),
        Qstr::MP_QSTR_WipeDevice => WIPE_DEVICE.as_obj(),
        Qstr::MP_QSTR_ScreenBrightness => SCREEN_BRIGHTNESS.as_obj(),
        Qstr::MP_QSTR_AutoLockDelay => AUTO_LOCK_DELAY.as_obj(),
        Qstr::MP_QSTR_DemoCreateWallet => DEMO_CREATE_WALLET.as_obj(),
        Qstr::MP_QSTR_DemoRestoreWallet => DEMO_RESTORE_WALLET.as_obj(),
        Qstr::MP_QSTR_DemoReceiveBitcoin => DEMO_RECEIVE_BITCOIN.as_obj(),
        Qstr::MP_QSTR_DemoSendBitcoin => DEMO_SEND_BITCOIN.as_obj(),
    } },
};

pub static DEVICE_MENU_RESULT: SimpleTypeObj = SimpleTypeObj::new(&DEVICE_MENU_RESULT_TYPE);
