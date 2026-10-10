use core::convert::TryInto;

use super::component::{
    AddressDetails, ButtonPage, CancelConfirmMsg, CoinJoinProgress, ConfirmHomescreen, Flow, Frame,
    Homescreen, Lockscreen, NumberInput, NumberInputAction, Page, PassphraseEntry, PinEntry,
    Progress, ScrollableFrame, WordlistEntry,
};
use crate::micropython::{Error, Obj};
use crate::ui::component::base::Component;
use crate::ui::component::paginated::{PageMsg, Paginate};
use crate::ui::component::text::paragraphs::{
    Checklist, ParagraphSource, ParagraphVecLong, Paragraphs,
};
use crate::ui::component::{FlowMsg, MsgMap, Never, Timeout};
use crate::ui::layout::obj::ComponentMsgObj;
use crate::ui::layout::result::{BACK, CANCELLED, CONFIRMED, INFO};

impl From<CancelConfirmMsg> for Obj {
    fn from(value: CancelConfirmMsg) -> Self {
        match value {
            CancelConfirmMsg::Cancelled => CANCELLED.as_obj(),
            CancelConfirmMsg::Confirmed => CONFIRMED.as_obj(),
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
            PageMsg::Cancelled if self.cancelled_is_back() => Ok(BACK.as_obj()),
            PageMsg::Cancelled => Ok(CANCELLED.as_obj()),
            PageMsg::Info => Ok(INFO.as_obj()),
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
            CancelConfirmMsg::Confirmed => {
                if let Some(index) = self.confirmed_index() {
                    index.try_into()
                } else {
                    Ok(CONFIRMED.as_obj())
                }
            }
            CancelConfirmMsg::Cancelled => Ok(CANCELLED.as_obj()),
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
        match msg {
            Self::Msg::Cancel => (CANCELLED.as_obj(), 0).try_into(),
            Self::Msg::Choice {
                item: NumberInputAction::Back,
                ..
            } => (BACK.as_obj(), 0).try_into(),
            Self::Msg::Choice {
                item: NumberInputAction::Number(n),
                ..
            } => (CONFIRMED.as_obj(), n).try_into(),
        }
    }
}

/// Layout returned by `show_checklist`: the checklist of backup steps with an
/// optional back button (up arrow) in place of the cancel button.
pub type ChecklistScreen =
    MsgMap<ButtonPage<Checklist<ParagraphVecLong<'static>>>, fn(PageMsg<Never>) -> Option<FlowMsg>>;

impl ComponentMsgObj for ChecklistScreen {
    fn msg_try_into_obj(&self, msg: Self::Msg) -> Result<Obj, Error> {
        // `TryFrom<FlowMsg> for Obj` covers all the emitted variants,
        // including `FlowMsg::Back`.
        msg.try_into()
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
    T: ComponentMsgObj + Paginate,
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
