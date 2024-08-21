use crate::{
    error,
    micropython::{map::Map, obj::Obj, qstr::Qstr, util},
    strutil::TString,
    translations::TR,
    ui::{
        component::{swipe_detect::SwipeSettings, ComponentExt, SwipeDirection},
        flow::{
            base::{DecisionBuilder as _, StateChange},
            FlowMsg, FlowState, SwipeFlow,
        },
        layout::obj::LayoutObj,
    },
};

use super::super::{
    component::{
        Frame, FrameMsg, PinKeyboard, PinKeyboardMsg, VerticalMenu, VerticalMenuChoiceMsg,
    },
    theme,
};

#[derive(Copy, Clone, PartialEq, Eq)]
pub enum RequestPin {
    Keypad,
    Menu,
}

impl FlowState for RequestPin {
    #[inline]
    fn index(&'static self) -> usize {
        *self as usize
    }

    fn handle_swipe(&'static self, direction: SwipeDirection) -> StateChange {
        match (self, direction) {
            (Self::Menu, SwipeDirection::Right) => Self::Keypad.transit(),
            _ => self.do_nothing(),
        }
    }

    fn handle_event(&'static self, msg: FlowMsg) -> StateChange {
        match (self, msg) {
            (Self::Keypad, FlowMsg::Cancelled) => Self::Menu.transit(),
            (Self::Keypad, FlowMsg::Text(s)) => self.return_msg(FlowMsg::Text(s)),
            (Self::Menu, FlowMsg::Cancelled) => Self::Keypad.swipe_right(),
            (Self::Menu, FlowMsg::Choice(0)) => self.return_msg(FlowMsg::Cancelled),
            _ => self.do_nothing(),
        }
    }
}

#[allow(clippy::not_unsafe_ptr_arg_deref)]
pub extern "C" fn new_request_pin(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, RequestPin::new_obj) }
}

impl RequestPin {
    fn new_obj(_args: &[Obj], kwargs: &Map) -> Result<Obj, error::Error> {
        let prompt: TString = kwargs.get(Qstr::MP_QSTR_prompt)?.try_into()?;
        let subprompt: TString = kwargs.get(Qstr::MP_QSTR_subprompt)?.try_into()?;
        let allow_cancel: bool = kwargs.get_or(Qstr::MP_QSTR_allow_cancel, true)?;
        let warning: bool = kwargs.get_or(Qstr::MP_QSTR_wrong_pin, false)?;
        let warning = if warning {
            Some(TR::pin__wrong_pin.into())
        } else {
            None
        };

        let content_menu = Frame::left_aligned(
            TString::empty(),
            VerticalMenu::empty().danger(theme::ICON_CANCEL, TR::buttons__cancel.into()),
        )
        .with_cancel_button()
        .with_swipe(SwipeDirection::Right, SwipeSettings::immediate())
        .map(|msg| match msg {
            FrameMsg::Content(VerticalMenuChoiceMsg::Selected(i)) => Some(FlowMsg::Choice(i)),
            FrameMsg::Button(_) => Some(FlowMsg::Cancelled),
        });

        let content_keypad =
            PinKeyboard::new(prompt, subprompt, warning, allow_cancel).map(|msg| match msg {
                PinKeyboardMsg::Confirmed(s) => Some(FlowMsg::Text(s)),
                PinKeyboardMsg::Cancelled => Some(FlowMsg::Cancelled),
            });

        let res = SwipeFlow::new(&RequestPin::Keypad)?
            .with_page(&RequestPin::Keypad, content_keypad)?
            .with_page(&RequestPin::Menu, content_menu)?;
        Ok(LayoutObj::new(res)?.into())
    }
}
