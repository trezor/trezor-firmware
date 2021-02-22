use core::convert::TryInto;

use crate::{
    micropython::obj::Obj,
    ui::{
        component::{ButtonContent, Component, Confirm, ConfirmMsg, Empty},
        display, theme,
    },
};

use super::layout::LayoutObj;

impl<T> Into<Obj> for ConfirmMsg<T>
where
    T: Component,
    T::Msg: Into<Obj>,
{
    fn into(self) -> Obj {
        match self {
            ConfirmMsg::Content(c) => c.into(),
            ConfirmMsg::LeftClicked => 1.try_into().unwrap(),
            ConfirmMsg::RightClicked => 2.try_into().unwrap(),
        }
    }
}

impl From<!> for Obj {
    fn from(_: !) -> Self {
        unreachable!()
    }
}

#[no_mangle]
extern "C" fn ui_layout_new_example() -> Obj {
    LayoutObj::new(Confirm::new(
        display::screen(),
        Empty::new(),
        Some(ButtonContent::Text("Left".as_bytes())),
        theme::button_default(),
        Some(ButtonContent::Text("Right".as_bytes())),
        theme::button_default(),
    ))
    .into()
}
