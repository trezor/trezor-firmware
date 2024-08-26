use crate::{
    error,
    micropython::{gc::Gc, list::List, map::Map, obj::Obj, qstr::Qstr, util},
    strutil::TString,
    translations::TR,
    ui::{
        component::{
            swipe_detect::SwipeSettings,
            text::paragraphs::{Paragraph, Paragraphs},
            ComponentExt, SwipeDirection,
        },
        flow::{
            base::{DecisionBuilder as _, StateChange},
            FlowMsg, FlowState, SwipeFlow,
        },
        layout::obj::LayoutObj,
    },
};

use super::super::{
    component::{
        ChooseCredential, FidoCredential, Frame, FrameMsg, PromptMsg, PromptScreen, SwipeContent,
        VerticalMenu, VerticalMenuChoiceMsg,
    },
    theme,
};

use core::sync::atomic::{AtomicBool, AtomicUsize, Ordering};

#[derive(Copy, Clone, PartialEq, Eq)]
pub enum ConfirmFido {
    Intro,
    ChooseCredential,
    Details,
    Tap,
    Menu,
}

static CRED_SELECTED: AtomicUsize = AtomicUsize::new(0);
static SINGLE_CRED: AtomicBool = AtomicBool::new(false);

impl FlowState for ConfirmFido {
    #[inline]
    fn index(&'static self) -> usize {
        *self as usize
    }

    fn handle_swipe(&'static self, direction: SwipeDirection) -> StateChange {
        match (self, direction) {
            (Self::Intro, SwipeDirection::Left) => Self::Menu.swipe(direction),
            (Self::Intro, SwipeDirection::Up) => Self::ChooseCredential.swipe(direction),
            (Self::ChooseCredential, SwipeDirection::Down) => Self::Intro.swipe(direction),
            (Self::Details, SwipeDirection::Up) => Self::Tap.swipe(direction),
            (Self::Tap, SwipeDirection::Down) => Self::Details.swipe(direction),
            _ => self.do_nothing(),
        }
    }

    fn handle_event(&'static self, msg: FlowMsg) -> StateChange {
        match (self, msg) {
            (_, FlowMsg::Info) => Self::Menu.transit(),
            (Self::Menu, FlowMsg::Choice(0)) => self.return_msg(FlowMsg::Cancelled),
            (Self::Menu, FlowMsg::Cancelled) => {
                if Self::single_cred() {
                    Self::Details.swipe_right()
                } else {
                    Self::Intro.swipe_right()
                }
            }
            (Self::ChooseCredential, FlowMsg::Choice(i)) => {
                CRED_SELECTED.store(i, Ordering::Relaxed);
                Self::Details.swipe_left()
            }
            (Self::Details, FlowMsg::Cancelled) => Self::ChooseCredential.swipe_right(),
            (Self::Tap, FlowMsg::Confirmed) => {
                self.return_msg(FlowMsg::Choice(CRED_SELECTED.load(Ordering::Relaxed)))
            }
            _ => self.do_nothing(),
        }
    }
}

#[allow(clippy::not_unsafe_ptr_arg_deref)]
pub extern "C" fn new_confirm_fido(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, ConfirmFido::new_obj) }
}

impl ConfirmFido {
    const EXTRA_PADDING: i16 = 6;

    fn single_cred() -> bool {
        SINGLE_CRED.load(Ordering::Relaxed)
    }

    fn new_obj(_args: &[Obj], kwargs: &Map) -> Result<Obj, error::Error> {
        let title: TString = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let app_name: TString = kwargs.get(Qstr::MP_QSTR_app_name)?.try_into()?;
        let icon_name: Option<TString> = kwargs.get(Qstr::MP_QSTR_icon_name)?.try_into_option()?;
        let accounts: Gc<List> = kwargs.get(Qstr::MP_QSTR_accounts)?.try_into()?;
        let num_accounts = accounts.len();
        SINGLE_CRED.store(num_accounts <= 1, Ordering::Relaxed);
        CRED_SELECTED.store(0, Ordering::Relaxed);

        let content_intro = Frame::left_aligned(
            title,
            SwipeContent::new(Paragraphs::new(Paragraph::new::<TString>(
                &theme::TEXT_MAIN_GREY_LIGHT,
                TR::fido__select_intro.into(),
            ))),
        )
        .with_menu_button()
        .with_footer(TR::instructions__swipe_up.into(), None)
        .with_swipe(SwipeDirection::Up, SwipeSettings::default())
        .with_swipe(SwipeDirection::Right, SwipeSettings::immediate())
        .map(|msg| matches!(msg, FrameMsg::Button(_)).then_some(FlowMsg::Info));

        // Closure to lazy-load the information on given page index.
        // Done like this to allow arbitrarily many pages without
        // the need of any allocation here in Rust.
        let label_fn = move |page_index| {
            let account = unwrap!(accounts.get(page_index));
            account
                .try_into()
                .unwrap_or_else(|_| TString::from_str("-"))
        };
        let content_choose_credential =
            ChooseCredential::new(label_fn, num_accounts).map(|msg| match msg {
                FrameMsg::Button(_) => Some(FlowMsg::Info),
                FrameMsg::Content(VerticalMenuChoiceMsg::Selected(i)) => Some(FlowMsg::Choice(i)),
            });

        let get_account = move || {
            let current = CRED_SELECTED.load(Ordering::Relaxed);
            let account = unwrap!(accounts.get(current));
            account.try_into().unwrap_or_else(|_| TString::from_str(""))
        };
        let content_details = Frame::left_aligned(
            TR::fido__title_credential_details.into(),
            SwipeContent::new(FidoCredential::new(icon_name, app_name, get_account)),
        )
        .with_footer(TR::instructions__swipe_up.into(), Some(title))
        .with_swipe(SwipeDirection::Up, SwipeSettings::default())
        .with_swipe(SwipeDirection::Right, SwipeSettings::immediate());
        let content_details = if Self::single_cred() {
            content_details.with_menu_button()
        } else {
            content_details.with_cancel_button()
        }
        .map(|msg| match msg {
            FrameMsg::Button(bm) => Some(bm),
            _ => None,
        });

        let content_tap = Frame::left_aligned(title, PromptScreen::new_tap_to_confirm())
            .with_menu_button()
            .with_footer(TR::instructions__tap_to_confirm.into(), None)
            .with_swipe(SwipeDirection::Down, SwipeSettings::default())
            .with_swipe(SwipeDirection::Right, SwipeSettings::immediate())
            .map(|msg| match msg {
                FrameMsg::Content(PromptMsg::Confirmed) => Some(FlowMsg::Confirmed),
                FrameMsg::Button(_) => Some(FlowMsg::Info),
                _ => None,
            });

        let content_menu = Frame::left_aligned(
            "".into(),
            VerticalMenu::empty().danger(theme::ICON_CANCEL, TR::buttons__cancel.into()),
        )
        .with_cancel_button()
        .with_swipe(SwipeDirection::Right, SwipeSettings::immediate())
        .map(|msg| match msg {
            FrameMsg::Content(VerticalMenuChoiceMsg::Selected(i)) => Some(FlowMsg::Choice(i)),
            FrameMsg::Button(_) => Some(FlowMsg::Cancelled),
        });

        let initial_page = if Self::single_cred() {
            &ConfirmFido::Details
        } else {
            &ConfirmFido::Intro
        };
        let res = SwipeFlow::new(initial_page)?
            .with_page(&ConfirmFido::Intro, content_intro)?
            .with_page(&ConfirmFido::ChooseCredential, content_choose_credential)?
            .with_page(&ConfirmFido::Details, content_details)?
            .with_page(&ConfirmFido::Tap, content_tap)?
            .with_page(&ConfirmFido::Menu, content_menu)?;
        Ok(LayoutObj::new(res)?.into())
    }
}
