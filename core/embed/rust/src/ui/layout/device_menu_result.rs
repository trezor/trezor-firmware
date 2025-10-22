use crate::{
    error::Error,
    micropython::{
        ffi, macros::obj_type, obj::Obj, qstr::Qstr, simple_type::SimpleTypeObj, typ::Type, util,
    },
};

use num_traits::ToPrimitive;

#[repr(u8)]
#[derive(Copy, Clone, ToPrimitive)]
pub enum DeviceMenuMsg {
    Close = 0,
    // Root menu
    ReviewFailedBackup,

    // "Pair & Connect"
    PairDevice,       // pair a new device
    DisconnectDevice, // disconnect a device
    UnpairDevice,     // unpair a device, its index is in result_arg
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
    ToggleHaptics,
    ToggleLed,
    WipeDevice,

    // Misc
    RefreshMenu, // menu id is in result_arg
}

impl DeviceMenuMsg {
    pub fn as_obj(&self) -> Obj {
        assert!(!matches!(self, DeviceMenuMsg::Close));
        let n = unwrap!(self.to_u8());
        n.into()
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
        let value = match attr {
            Qstr::MP_QSTR_ReviewFailedBackup => DeviceMenuMsg::ReviewFailedBackup.as_obj(),
            Qstr::MP_QSTR_PairDevice => DeviceMenuMsg::PairDevice.as_obj(),
            Qstr::MP_QSTR_DisconnectDevice => DeviceMenuMsg::DisconnectDevice.as_obj(),
            Qstr::MP_QSTR_UnpairDevice => DeviceMenuMsg::UnpairDevice.as_obj(),
            Qstr::MP_QSTR_UnpairAllDevices => DeviceMenuMsg::UnpairAllDevices.as_obj(),
            Qstr::MP_QSTR_ToggleBluetooth => DeviceMenuMsg::ToggleBluetooth.as_obj(),
            Qstr::MP_QSTR_SetOrChangePin => DeviceMenuMsg::SetOrChangePin.as_obj(),
            Qstr::MP_QSTR_RemovePin => DeviceMenuMsg::RemovePin.as_obj(),
            Qstr::MP_QSTR_SetAutoLockBattery => DeviceMenuMsg::SetAutoLockBattery.as_obj(),
            Qstr::MP_QSTR_SetAutoLockUSB => DeviceMenuMsg::SetAutoLockUSB.as_obj(),
            Qstr::MP_QSTR_SetOrChangeWipeCode => DeviceMenuMsg::SetOrChangeWipeCode.as_obj(),
            Qstr::MP_QSTR_RemoveWipeCode => DeviceMenuMsg::RemoveWipeCode.as_obj(),
            Qstr::MP_QSTR_CheckBackup => DeviceMenuMsg::CheckBackup.as_obj(),
            Qstr::MP_QSTR_SetDeviceName => DeviceMenuMsg::SetDeviceName.as_obj(),
            Qstr::MP_QSTR_SetBrightness => DeviceMenuMsg::SetBrightness.as_obj(),
            Qstr::MP_QSTR_ToggleHaptics => DeviceMenuMsg::ToggleHaptics.as_obj(),
            Qstr::MP_QSTR_ToggleLed => DeviceMenuMsg::ToggleLed.as_obj(),
            Qstr::MP_QSTR_WipeDevice => DeviceMenuMsg::WipeDevice.as_obj(),
            Qstr::MP_QSTR_TurnOff => DeviceMenuMsg::TurnOff.as_obj(),
            Qstr::MP_QSTR_Reboot => DeviceMenuMsg::Reboot.as_obj(),
            Qstr::MP_QSTR_RebootToBootloader => DeviceMenuMsg::RebootToBootloader.as_obj(),
            Qstr::MP_QSTR_RefreshMenu => DeviceMenuMsg::RefreshMenu.as_obj(),
            _ => return Err(Error::AttributeError(attr)),
        };
        unsafe { dest.write(value) };
        Ok(())
    };
    unsafe { util::try_or_raise(block) }
}

pub static DEVICE_MENU_RESULT: SimpleTypeObj = SimpleTypeObj::new(&DEVICE_MENU_RESULT_TYPE);
