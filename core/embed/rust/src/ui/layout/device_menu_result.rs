use crate::{
    error::Error,
    micropython::{
        ffi, macros::obj_type, obj::Obj, qstr::Qstr, simple_type::SimpleTypeObj, typ::Type, util,
    },
};

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
static DEVICE_MENU_RESULT_TYPE: Type = obj_type! {
    name: Qstr::MP_QSTR_DeviceMenuResult,
    attr_fn: device_menu_result_attr,
};

unsafe extern "C" fn device_menu_result_attr(_self_in: Obj, attr: ffi::qstr, dest: *mut Obj) {
    let block = || {
        let arg = unsafe { dest.read() };
        if !arg.is_null() {
            // Null destination would mean a `setattr`.
            return Err(Error::TypeError);
        }
        let attr = Qstr::from_u16(attr as _);
        let msg = match attr {
            Qstr::MP_QSTR_Close => Qstr::MP_QSTR_Close,
            Qstr::MP_QSTR_ReviewFailedBackup => Qstr::MP_QSTR_ReviewFailedBackup,
            Qstr::MP_QSTR_PairDevice => Qstr::MP_QSTR_PairDevice,
            Qstr::MP_QSTR_DisconnectDevice => Qstr::MP_QSTR_DisconnectDevice,
            Qstr::MP_QSTR_UnpairDevice => Qstr::MP_QSTR_UnpairDevice,
            Qstr::MP_QSTR_UnpairAllDevices => Qstr::MP_QSTR_UnpairAllDevices,
            Qstr::MP_QSTR_ToggleBluetooth => Qstr::MP_QSTR_ToggleBluetooth,
            Qstr::MP_QSTR_SetOrChangePin => Qstr::MP_QSTR_SetOrChangePin,
            Qstr::MP_QSTR_RemovePin => Qstr::MP_QSTR_RemovePin,
            Qstr::MP_QSTR_SetAutoLockBattery => Qstr::MP_QSTR_SetAutoLockBattery,
            Qstr::MP_QSTR_SetAutoLockUSB => Qstr::MP_QSTR_SetAutoLockUSB,
            Qstr::MP_QSTR_SetOrChangeWipeCode => Qstr::MP_QSTR_SetOrChangeWipeCode,
            Qstr::MP_QSTR_RemoveWipeCode => Qstr::MP_QSTR_RemoveWipeCode,
            Qstr::MP_QSTR_CheckBackup => Qstr::MP_QSTR_CheckBackup,
            Qstr::MP_QSTR_SetDeviceName => Qstr::MP_QSTR_SetDeviceName,
            Qstr::MP_QSTR_SetBrightness => Qstr::MP_QSTR_SetBrightness,
            Qstr::MP_QSTR_ToggleTapToWake => Qstr::MP_QSTR_ToggleTapToWake,
            Qstr::MP_QSTR_ToggleHaptics => Qstr::MP_QSTR_ToggleHaptics,
            Qstr::MP_QSTR_ToggleLed => Qstr::MP_QSTR_ToggleLed,
            Qstr::MP_QSTR_WipeDevice => Qstr::MP_QSTR_WipeDevice,
            Qstr::MP_QSTR_TurnOff => Qstr::MP_QSTR_TurnOff,
            Qstr::MP_QSTR_Reboot => Qstr::MP_QSTR_Reboot,
            Qstr::MP_QSTR_RebootToBootloader => Qstr::MP_QSTR_RebootToBootloader,
            Qstr::MP_QSTR_RefreshMenu => Qstr::MP_QSTR_RefreshMenu,
            _ => return Err(Error::AttributeError(attr)),
        };
        unsafe { dest.write(msg.to_obj()) };
        Ok(())
    };
    unsafe { util::try_or_raise(block) }
}

pub static DEVICE_MENU_RESULT: SimpleTypeObj = SimpleTypeObj::new(&DEVICE_MENU_RESULT_TYPE);
