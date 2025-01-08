use core::convert::TryInto;

use super::component::{
    AddressDetails, ButtonPage, CancelConfirmMsg, CancelInfoConfirmMsg, CoinJoinProgress,
    ConfirmHomescreen, Flow, Frame, Homescreen, Lockscreen, NumberInput, Page, PassphraseEntry,
    PinEntry, Progress, ScrollableContent, ScrollableFrame, ShowMore, SimpleChoice, WordlistEntry,
};
use crate::{
    error::Error,
    micropython::obj::Obj,
    ui::{
        component::{
            base::Component,
            paginated::{PageMsg, Paginate},
            text::paragraphs::{ParagraphSource, Paragraphs},
            Never, Timeout,
        },
        layout::{
            obj::ComponentMsgObj,
            result::{CANCELLED, CONFIRMED, INFO},
        },
    },
};

impl From<CancelConfirmMsg> for Obj {
    fn from(value: CancelConfirmMsg) -> Self {
        match value {
            CancelConfirmMsg::Cancelled => CANCELLED.as_obj(),
            CancelConfirmMsg::Confirmed => CONFIRMED.as_obj(),
        }
    }
}

impl<T> ComponentMsgObj for ShowMore<T>
where
    T: Component<Msg = Never>,
{
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        match msg {
            CancelInfoConfirmMsg::Cancelled => Ok(CANCELLED.as_obj()),
            CancelInfoConfirmMsg::Info => Ok(INFO.as_obj()),
            CancelInfoConfirmMsg::Confirmed => Ok(CONFIRMED.as_obj()),
        }
    }
}

impl<'a, T> ComponentMsgObj for Paragraphs<T>
where
    T: ParagraphSource<'a>,
{
    fn msg_try_into_obj(&self, _msg: Self::Msg) -> Result<Obj, Error> {
        unreachable!()
    }
}

impl<T> ComponentMsgObj for ButtonPage<T>
where
    T: Component + Paginate,
{
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        match msg {
            PageMsg::Confirmed => Ok(CONFIRMED.as_obj()),
            PageMsg::Cancelled => Ok(CANCELLED.as_obj()),
            _ => Err(Error::TypeError),
        }
    }
}

impl<F> ComponentMsgObj for Flow<F>
where
    F: Fn(usize) -> Page,
{
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        match msg {
            CancelInfoConfirmMsg::Confirmed => {
                if let Some(index) = self.confirmed_index() {
                    index.try_into()
                } else {
                    Ok(CONFIRMED.as_obj())
                }
            }
            CancelInfoConfirmMsg::Cancelled => Ok(CANCELLED.as_obj()),
            CancelInfoConfirmMsg::Info => Ok(INFO.as_obj()),
        }
    }
}

impl ComponentMsgObj for PinEntry<'_> {
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        match msg {
            CancelConfirmMsg::Confirmed => self.pin().try_into(),
            CancelConfirmMsg::Cancelled => Ok(CANCELLED.as_obj()),
        }
    }
}

impl<T> ComponentMsgObj for (Timeout, T)
where
    T: Component<Msg = ()>,
{
    fn msg_try_into_obj(&self, _msg: Self::Msg) -> Result<Obj, Error> {
        Ok(CANCELLED.as_obj())
    }
}

impl ComponentMsgObj for AddressDetails {
    fn msg_try_into_obj(&self, _msg: Self::Msg) -> Result<Obj, Error> {
        Ok(CANCELLED.as_obj())
    }
}

impl ComponentMsgObj for CoinJoinProgress {
    fn msg_try_into_obj(&self, _msg: Self::Msg) -> Result<Obj, Error> {
        unreachable!();
    }
}

impl ComponentMsgObj for NumberInput {
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        (CONFIRMED.as_obj(), msg.try_into()?).try_into()
    }
}

impl ComponentMsgObj for SimpleChoice {
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        if self.return_index {
            msg.try_into()
        } else {
            let text = self.result_by_index(msg);
            text.try_into()
        }
    }
}

impl ComponentMsgObj for WordlistEntry {
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        msg.try_into()
    }
}

impl ComponentMsgObj for PassphraseEntry {
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        match msg {
            CancelConfirmMsg::Confirmed => self.passphrase().try_into(),
            CancelConfirmMsg::Cancelled => Ok(CANCELLED.as_obj()),
        }
    }
}

impl<T> ComponentMsgObj for Frame<T>
where
    T: ComponentMsgObj,
{
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        self.inner().msg_try_into_obj(msg)
    }
}

impl<T> ComponentMsgObj for ScrollableFrame<T>
where
    T: ComponentMsgObj + ScrollableContent,
{
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        self.inner().msg_try_into_obj(msg)
    }
}

impl ComponentMsgObj for Progress {
    fn msg_try_into_obj(&self, _msg: Self::Msg) -> Result<Obj, Error> {
        unreachable!()
    }
}

impl ComponentMsgObj for Homescreen {
    fn msg_try_into_obj(&self, _msg: Self::Msg) -> Result<Obj, Error> {
        Ok(CANCELLED.as_obj())
    }
}

impl<'a> ComponentMsgObj for Lockscreen<'a> {
    fn msg_try_into_obj(&self, _msg: Self::Msg) -> Result<Obj, Error> {
        Ok(CANCELLED.as_obj())
    }
}

impl ComponentMsgObj for ConfirmHomescreen {
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        match msg {
            CancelConfirmMsg::Confirmed => Ok(CONFIRMED.as_obj()),
            CancelConfirmMsg::Cancelled => Ok(CANCELLED.as_obj()),
        }
    }
}

impl ComponentMsgObj for super::component::bl_confirm::Confirm<'_> {
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        match msg {
            super::component::bl_confirm::ConfirmMsg::Cancel => Ok(CANCELLED.as_obj()),
            super::component::bl_confirm::ConfirmMsg::Confirm => Ok(CONFIRMED.as_obj()),
        }
    }
}
