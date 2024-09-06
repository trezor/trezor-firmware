use crate::{
    error,
    micropython::{map::Map, obj::Obj, qstr::Qstr, util},
    strutil::{ShortString, TString},
    translations::TR,
    ui::{
        component::ComponentExt,
        flow::{
            base::{Decision, DecisionBuilder as _},
            FlowController, FlowMsg, SwipeFlow,
        },
        geometry::Direction,
        layout::obj::LayoutObj,
    },
};

use super::super::component::{
    Frame, FrameMsg, PassphraseKeyboard, PassphraseKeyboardMsg, PromptMsg, PromptScreen,
};

#[derive(Copy, Clone, PartialEq, Eq)]
pub enum RequestPassphrase {
    Keypad,
    ConfirmEmpty,
}

impl FlowController for RequestPassphrase {
    #[inline]
    fn index(&'static self) -> usize {
        *self as usize
    }

    fn handle_swipe(&'static self, _direction: Direction) -> Decision {
        self.do_nothing()
    }

    fn handle_event(&'static self, msg: FlowMsg) -> Decision {
        match (self, msg) {
            (Self::Keypad, FlowMsg::Text(s)) => {
                if s.is_empty() {
                    Self::ConfirmEmpty.goto()
                } else {
                    self.return_msg(FlowMsg::Text(s))
                }
            }
            (Self::Keypad, FlowMsg::Cancelled) => self.return_msg(FlowMsg::Cancelled),
            (Self::ConfirmEmpty, FlowMsg::Cancelled) => Self::Keypad.goto(),
            (Self::ConfirmEmpty, FlowMsg::Confirmed) => {
                self.return_msg(FlowMsg::Text(ShortString::new()))
            }
            _ => self.do_nothing(),
        }
    }
}

#[allow(clippy::not_unsafe_ptr_arg_deref)]
pub extern "C" fn new_request_passphrase(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, RequestPassphrase::new_obj) }
}

impl RequestPassphrase {
    fn new_obj(_args: &[Obj], kwargs: &Map) -> Result<Obj, error::Error> {
        let _prompt: TString = kwargs.get(Qstr::MP_QSTR_prompt)?.try_into()?;
        let _max_len: u32 = kwargs.get(Qstr::MP_QSTR_max_len)?.try_into()?;

        let content_confirm_empty = Frame::left_aligned(
            TR::passphrase__continue_with_empty_passphrase.into(),
            PromptScreen::new_yes_or_no(),
        )
        .map(|msg| match msg {
            FrameMsg::Content(PromptMsg::Confirmed) => Some(FlowMsg::Confirmed),
            FrameMsg::Content(PromptMsg::Cancelled) => Some(FlowMsg::Cancelled),
            _ => None,
        });

        let content_keypad = PassphraseKeyboard::new().map(|msg| match msg {
            PassphraseKeyboardMsg::Confirmed(s) => Some(FlowMsg::Text(s)),
            PassphraseKeyboardMsg::Cancelled => Some(FlowMsg::Cancelled),
        });

        let res = SwipeFlow::new(&RequestPassphrase::Keypad)?
            .with_page(&RequestPassphrase::Keypad, content_keypad)?
            .with_page(&RequestPassphrase::ConfirmEmpty, content_confirm_empty)?;
        Ok(LayoutObj::new(res)?.into())
    }
}
