use crate::micropython::macros::{obj_dict, obj_map, obj_type};
use crate::micropython::qstr::Qstr;
use crate::micropython::simple_type::SimpleTypeObj;
use crate::micropython::typ::FullType;
use crate::micropython::Obj;

#[derive(Copy, Clone)]
pub enum DeviceMenuMsg {
    Close,
    // Root menu
    ReviewFailedBackup,

    // "Pair & Connect"
    PairDevice,       // pair a new device
    DisconnectDevice, // disconnect a device
    UnpairDevice(u8), // unpair a device
    UnpairAllDevices,

    // Power
    TurnOff,
    Reboot,
    RebootToBootloader,

    // Settings menu
    ToggleBluetooth,

    // Security menu
    SetOrChangePin,
    RemovePin,
    SetAutoLockBattery,
    SetAutoLockUSB,
    SetOrChangeWipeCode,
    RemoveWipeCode,
    CheckBackup,

    // Device menu
    SetDeviceName,
    SetBrightness,
    ToggleTapToWake,
    ToggleHaptics,
    ToggleLed,
    WipeDevice,

    // Misc
    RefreshMenu,
}

impl DeviceMenuMsg {
    pub fn id_to_obj(&self) -> Obj {
        match self {
            Self::Close => Qstr::MP_QSTR_Close,
            Self::ReviewFailedBackup => Qstr::MP_QSTR_ReviewFailedBackup,
            Self::PairDevice => Qstr::MP_QSTR_PairDevice,
            Self::DisconnectDevice => Qstr::MP_QSTR_DisconnectDevice,
            Self::UnpairDevice(_) => Qstr::MP_QSTR_UnpairDevice,
            Self::UnpairAllDevices => Qstr::MP_QSTR_UnpairAllDevices,
            Self::TurnOff => Qstr::MP_QSTR_TurnOff,
            Self::Reboot => Qstr::MP_QSTR_Reboot,
            Self::RebootToBootloader => Qstr::MP_QSTR_RebootToBootloader,
            Self::ToggleBluetooth => Qstr::MP_QSTR_ToggleBluetooth,
            Self::SetOrChangePin => Qstr::MP_QSTR_SetOrChangePin,
            Self::RemovePin => Qstr::MP_QSTR_RemovePin,
            Self::SetAutoLockBattery => Qstr::MP_QSTR_SetAutoLockBattery,
            Self::SetAutoLockUSB => Qstr::MP_QSTR_SetAutoLockUSB,
            Self::SetOrChangeWipeCode => Qstr::MP_QSTR_SetOrChangeWipeCode,
            Self::RemoveWipeCode => Qstr::MP_QSTR_RemoveWipeCode,
            Self::CheckBackup => Qstr::MP_QSTR_CheckBackup,
            Self::SetDeviceName => Qstr::MP_QSTR_SetDeviceName,
            Self::SetBrightness => Qstr::MP_QSTR_SetBrightness,
            Self::ToggleTapToWake => Qstr::MP_QSTR_ToggleTapToWake,
            Self::ToggleHaptics => Qstr::MP_QSTR_ToggleHaptics,
            Self::ToggleLed => Qstr::MP_QSTR_ToggleLed,
            Self::WipeDevice => Qstr::MP_QSTR_WipeDevice,
            Self::RefreshMenu => Qstr::MP_QSTR_RefreshMenu,
        }
        .to_obj()
    }

    pub fn args_to_obj(&self) -> Obj {
        match self {
            Self::UnpairDevice(id) => (*id).into(),
            _ => Obj::const_none(),
        }
    }
}

// Create a DeviceMenuResult class that contains all result types
static DEVICE_MENU_RESULT_TYPE: FullType = obj_type! {
    name: Qstr::MP_QSTR_DeviceMenuResult,
    locals: &obj_dict!(obj_map! {
        Qstr::MP_QSTR_Close => Qstr::MP_QSTR_Close.to_obj(),
        Qstr::MP_QSTR_ReviewFailedBackup => Qstr::MP_QSTR_ReviewFailedBackup.to_obj(),
        Qstr::MP_QSTR_PairDevice => Qstr::MP_QSTR_PairDevice.to_obj(),
        Qstr::MP_QSTR_DisconnectDevice => Qstr::MP_QSTR_DisconnectDevice.to_obj(),
        Qstr::MP_QSTR_UnpairDevice => Qstr::MP_QSTR_UnpairDevice.to_obj(),
        Qstr::MP_QSTR_UnpairAllDevices => Qstr::MP_QSTR_UnpairAllDevices.to_obj(),
        Qstr::MP_QSTR_TurnOff => Qstr::MP_QSTR_TurnOff.to_obj(),
        Qstr::MP_QSTR_Reboot => Qstr::MP_QSTR_Reboot.to_obj(),
        Qstr::MP_QSTR_RebootToBootloader => Qstr::MP_QSTR_RebootToBootloader.to_obj(),
        Qstr::MP_QSTR_ToggleBluetooth => Qstr::MP_QSTR_ToggleBluetooth.to_obj(),
        Qstr::MP_QSTR_SetOrChangePin => Qstr::MP_QSTR_SetOrChangePin.to_obj(),
        Qstr::MP_QSTR_RemovePin => Qstr::MP_QSTR_RemovePin.to_obj(),
        Qstr::MP_QSTR_SetAutoLockBattery => Qstr::MP_QSTR_SetAutoLockBattery.to_obj(),
        Qstr::MP_QSTR_SetAutoLockUSB => Qstr::MP_QSTR_SetAutoLockUSB.to_obj(),
        Qstr::MP_QSTR_SetOrChangeWipeCode => Qstr::MP_QSTR_SetOrChangeWipeCode.to_obj(),
        Qstr::MP_QSTR_RemoveWipeCode => Qstr::MP_QSTR_RemoveWipeCode.to_obj(),
        Qstr::MP_QSTR_CheckBackup => Qstr::MP_QSTR_CheckBackup.to_obj(),
        Qstr::MP_QSTR_SetDeviceName => Qstr::MP_QSTR_SetDeviceName.to_obj(),
        Qstr::MP_QSTR_SetBrightness => Qstr::MP_QSTR_SetBrightness.to_obj(),
        Qstr::MP_QSTR_ToggleTapToWake => Qstr::MP_QSTR_ToggleTapToWake.to_obj(),
        Qstr::MP_QSTR_ToggleHaptics => Qstr::MP_QSTR_ToggleHaptics.to_obj(),
        Qstr::MP_QSTR_ToggleLed => Qstr::MP_QSTR_ToggleLed.to_obj(),
        Qstr::MP_QSTR_WipeDevice => Qstr::MP_QSTR_WipeDevice.to_obj(),
        Qstr::MP_QSTR_RefreshMenu => Qstr::MP_QSTR_RefreshMenu.to_obj(),
    }),
};

pub static DEVICE_MENU_RESULT: SimpleTypeObj = SimpleTypeObj::new(&DEVICE_MENU_RESULT_TYPE);
