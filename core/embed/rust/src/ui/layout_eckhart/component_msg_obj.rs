use crate::{
    error::Error,
    micropython::obj::Obj,
    ui::{
        component::{
            text::paragraphs::{ParagraphSource, Paragraphs},
            Component, Timeout,
        },
        layout::{
            obj::ComponentMsgObj,
            result::{CANCELLED, CONFIRMED, INFO},
        },
    },
};

use super::component::{AllowedTextContent, TextScreen, TextScreenMsg};

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
