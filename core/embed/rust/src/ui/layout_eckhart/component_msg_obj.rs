#[cfg(not(feature = "clippy"))]
use crate::ui::component::{
    text::paragraphs::{ParagraphSource, Paragraphs},
    Component, Timeout,
};
use crate::{
    error::Error,
    micropython::{obj::Obj, util::new_tuple},
    ui::layout::{
        device_menu_result::*,
        obj::ComponentMsgObj,
        result::{CANCELLED, CONFIRMED, INFO},
    },
};

use super::firmware::{
    AllowedTextContent, ConfirmHomescreen, ConfirmHomescreenMsg, DeviceMenuMsg, DeviceMenuScreen,
    Homescreen, HomescreenMsg, MnemonicInput, MnemonicKeyboard, MnemonicKeyboardMsg, PinKeyboard,
    PinKeyboardMsg, ProgressScreen, SelectWordCountMsg, SelectWordCountScreen, SelectWordMsg,
    SelectWordScreen, SetBrightnessScreen, StringInput, StringKeyboard, StringKeyboardMsg,
    TextScreen, TextScreenMsg, ValueInput, ValueInputScreen, ValueInputScreenMsg,
};

impl ComponentMsgObj for PinKeyboard<'_> {
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        match msg {
            PinKeyboardMsg::Confirmed => self.pin().try_into(),
            PinKeyboardMsg::Cancelled => Ok(CANCELLED.as_obj()),
        }
    }
}

impl<I: StringInput> ComponentMsgObj for StringKeyboard<I> {
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        match msg {
            StringKeyboardMsg::Confirmed(content) => content.as_str().try_into(),
            StringKeyboardMsg::Cancelled => Ok(CANCELLED.as_obj()),
        }
    }
}

impl<T> ComponentMsgObj for MnemonicKeyboard<T>
where
    T: MnemonicInput,
{
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        match msg {
            MnemonicKeyboardMsg::Confirmed => {
                if let Some(word) = self.mnemonic() {
                    word.try_into()
                } else {
                    fatal_error!("Invalid mnemonic")
                }
            }
            MnemonicKeyboardMsg::Previous => "".try_into(),
        }
    }
}

// Clippy/compiler complains about conflicting implementations
// TODO move the common impls to a common module
#[cfg(not(feature = "clippy"))]
impl<'a, T> ComponentMsgObj for Paragraphs<T>
where
    T: ParagraphSource<'a>,
{
    fn msg_try_into_obj(&self, _msg: Self::Msg) -> Result<Obj, Error> {
        unreachable!()
    }
}

// Clippy/compiler complains about conflicting implementations
#[cfg(not(feature = "clippy"))]
impl<T> ComponentMsgObj for (Timeout, T)
where
    T: Component<Msg = ()>,
{
    fn msg_try_into_obj(&self, _msg: Self::Msg) -> Result<Obj, Error> {
        Ok(CANCELLED.as_obj())
    }
}

impl ComponentMsgObj for Homescreen {
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        match msg {
            HomescreenMsg::Dismissed => Ok(CANCELLED.as_obj()),
            HomescreenMsg::Menu => Ok(INFO.as_obj()),
        }
    }
}

impl ComponentMsgObj for ProgressScreen {
    fn msg_try_into_obj(&self, _msg: Self::Msg) -> Result<Obj, Error> {
        unreachable!()
    }
}

impl<T> ComponentMsgObj for TextScreen<T>
where
    T: AllowedTextContent,
{
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        match msg {
            TextScreenMsg::Cancelled => Ok(CANCELLED.as_obj()),
            TextScreenMsg::Confirmed => Ok(CONFIRMED.as_obj()),
            TextScreenMsg::Menu => Ok(INFO.as_obj()),
        }
    }
}

impl ComponentMsgObj for SelectWordScreen {
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        match msg {
            SelectWordMsg::Selected(i) => i.try_into(),
            SelectWordMsg::Cancelled => Ok(CANCELLED.as_obj()),
        }
    }
}

impl ComponentMsgObj for SelectWordCountScreen {
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        match msg {
            SelectWordCountMsg::Selected(i) => i.try_into(),
            SelectWordCountMsg::Cancelled => Ok(CANCELLED.as_obj()),
        }
    }
}

impl<T: ValueInput> ComponentMsgObj for ValueInputScreen<T> {
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        match msg {
            ValueInputScreenMsg::Confirmed(i) => i.try_into(),
            ValueInputScreenMsg::Cancelled => Ok(CANCELLED.as_obj()),
            // menu message is handled only in the flow
            ValueInputScreenMsg::Menu => unreachable!(),
            // changed value message is handled only in the flow
            ValueInputScreenMsg::Changed(_) => unreachable!(),
        }
    }
}

impl ComponentMsgObj for ConfirmHomescreen {
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        match msg {
            ConfirmHomescreenMsg::Cancelled => Ok(CANCELLED.as_obj()),
            ConfirmHomescreenMsg::Confirmed => Ok(CONFIRMED.as_obj()),
        }
    }
}

impl ComponentMsgObj for SetBrightnessScreen {
    fn msg_try_into_obj(&self, _msg: Self::Msg) -> Result<Obj, Error> {
        Ok(CONFIRMED.as_obj())
    }
}

impl ComponentMsgObj for DeviceMenuScreen {
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        match msg {
            // Root menu
            DeviceMenuMsg::ReviewFailedBackup => Ok(REVIEW_FAILED_BACKUP.as_obj()),
            // "Pair & Connect"
            DeviceMenuMsg::PairDevice => Ok(PAIR_DEVICE.as_obj()),
            DeviceMenuMsg::DisconnectDevice => Ok(DISCONNECT_DEVICE.as_obj()),
            DeviceMenuMsg::UnpairDevice(index) => {
                Ok(new_tuple(&[UNPAIR_DEVICE.as_obj(), index.into()])?)
            }
            DeviceMenuMsg::UnpairAllDevices => Ok(UNPAIR_ALL_DEVICES.as_obj()),
            // Settings
            DeviceMenuMsg::ToggleBluetooth => Ok(TOGGLE_BLUETOOTH.as_obj()),

            // Security menu
            DeviceMenuMsg::SetOrChangePin => Ok(SET_OR_CHANGE_PIN.as_obj()),
            DeviceMenuMsg::RemovePin => Ok(REMOVE_PIN.as_obj()),
            DeviceMenuMsg::SetAutoLockBattery => Ok(SET_AUTO_LOCK_BATTERY.as_obj()),
            DeviceMenuMsg::SetAutoLockUSB => Ok(SET_AUTO_LOCK_USB.as_obj()),
            DeviceMenuMsg::SetOrChangeWipeCode => Ok(SET_OR_CHANGE_WIPE_CODE.as_obj()),
            DeviceMenuMsg::RemoveWipeCode => Ok(REMOVE_WIPE_CODE.as_obj()),
            DeviceMenuMsg::CheckBackup => Ok(CHECK_BACKUP.as_obj()),
            // Device menu
            DeviceMenuMsg::SetDeviceName => Ok(SET_DEVICE_NAME.as_obj()),
            DeviceMenuMsg::SetBrightness => Ok(SET_BRIGHTNESS.as_obj()),
            DeviceMenuMsg::ToggleHaptics => Ok(TOGGLE_HAPTICS.as_obj()),
            DeviceMenuMsg::ToggleLed => Ok(TOGGLE_LED.as_obj()),
            DeviceMenuMsg::WipeDevice => Ok(WIPE_DEVICE.as_obj()),
            // Power settings
            DeviceMenuMsg::TurnOff => Ok(TURN_OFF.as_obj()),
            DeviceMenuMsg::Reboot => Ok(REBOOT.as_obj()),
            DeviceMenuMsg::RebootToBootloader => Ok(REBOOT_TO_BOOTLOADER.as_obj()),
            // Misc
            DeviceMenuMsg::RefreshMenu(submenu_id) => {
                let submenu_idx: u8 = submenu_id.into();
                Ok(new_tuple(&[REFRESH_MENU.as_obj(), submenu_idx.into()])?)
            }
            DeviceMenuMsg::Close => Ok(CANCELLED.as_obj()),
            // Demo
            DeviceMenuMsg::DemoCreateWallet => Ok(DEMO_CREATE_WALLET.as_obj()),
            DeviceMenuMsg::DemoRestoreWallet => Ok(DEMO_RESTORE_WALLET.as_obj()),
            DeviceMenuMsg::DemoReceiveBitcoin => Ok(DEMO_RECEIVE_BITCOIN.as_obj()),
            DeviceMenuMsg::DemoSendBitcoin => Ok(DEMO_SEND_BITCOIN.as_obj()),
            DeviceMenuMsg::DemoSwapAssets => Ok(DEMO_SWAP_ASSETS.as_obj()),
            DeviceMenuMsg::DemoApproveContract => Ok(DEMO_APPROVE_CONTRACT.as_obj()),
        }
    }
}
