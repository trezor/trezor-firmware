use crate::{
    error,
    micropython::{map::Map, obj::Obj, qstr::Qstr, util},
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
        CancelInfoConfirmMsg, Frame, FrameMsg, PromptScreen, SwipeContent, VerticalMenu,
        VerticalMenuChoiceMsg,
    },
    theme,
};

#[derive(Copy, Clone, PartialEq, Eq)]
pub enum ConfirmFirmwareUpdate {
    Intro,
    Menu,
    Fingerprint,
    Confirm,
}

impl FlowState for ConfirmFirmwareUpdate {
    #[inline]
    fn index(&'static self) -> usize {
        *self as usize
    }

    fn handle_swipe(&'static self, direction: SwipeDirection) -> StateChange {
        match (self, direction) {
            (Self::Intro, SwipeDirection::Left) => Self::Menu.swipe(direction),
            (Self::Intro, SwipeDirection::Up) => Self::Confirm.swipe(direction),
            (Self::Menu, SwipeDirection::Right) => Self::Intro.swipe(direction),
            (Self::Fingerprint, SwipeDirection::Right) => Self::Menu.swipe(direction),
            (Self::Confirm, SwipeDirection::Down) => Self::Intro.swipe(direction),
            (Self::Confirm, SwipeDirection::Left) => Self::Menu.swipe(direction),
            _ => self.do_nothing(),
        }
    }

    fn handle_event(&'static self, msg: FlowMsg) -> StateChange {
        match (self, msg) {
            (Self::Intro, FlowMsg::Info) => Self::Menu.transit(),
            (Self::Menu, FlowMsg::Cancelled) => Self::Intro.swipe_right(),
            (Self::Menu, FlowMsg::Choice(0)) => Self::Fingerprint.transit(),
            (Self::Menu, FlowMsg::Choice(1)) => self.return_msg(FlowMsg::Cancelled),
            (Self::Fingerprint, FlowMsg::Cancelled) => Self::Menu.transit(),
            (Self::Confirm, FlowMsg::Confirmed) => self.return_msg(FlowMsg::Confirmed),
            (Self::Confirm, FlowMsg::Info) => Self::Menu.transit(),
            _ => self.do_nothing(),
        }
    }
}

#[allow(clippy::not_unsafe_ptr_arg_deref)]
pub extern "C" fn new_confirm_firmware_update(
    n_args: usize,
    args: *const Obj,
    kwargs: *mut Map,
) -> Obj {
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, ConfirmFirmwareUpdate::new_obj) }
}

impl ConfirmFirmwareUpdate {
    fn new_obj(_args: &[Obj], kwargs: &Map) -> Result<Obj, error::Error> {
        let description: TString = kwargs.get(Qstr::MP_QSTR_description)?.try_into()?;
        let fingerprint: TString = kwargs.get(Qstr::MP_QSTR_fingerprint)?.try_into()?;

        let paragraphs = Paragraphs::new(Paragraph::new(&theme::TEXT_MAIN_GREY_LIGHT, description));
        let content_intro = Frame::left_aligned(
            TR::firmware_update__title.into(),
            SwipeContent::new(paragraphs),
        )
        .with_menu_button()
        .with_footer(TR::instructions__swipe_up.into(), None)
        .with_swipe(SwipeDirection::Up, SwipeSettings::default())
        .with_swipe(SwipeDirection::Left, SwipeSettings::default())
        .map(|msg| {
            matches!(msg, FrameMsg::Button(CancelInfoConfirmMsg::Info)).then_some(FlowMsg::Info)
        });

        let content_menu = Frame::left_aligned(
            TString::empty(),
            VerticalMenu::empty()
                .item(
                    theme::ICON_CHEVRON_RIGHT,
                    TR::firmware_update__title_fingerprint.into(),
                )
                .danger(theme::ICON_CANCEL, TR::buttons__cancel.into()),
        )
        .with_cancel_button()
        .with_swipe(SwipeDirection::Right, SwipeSettings::immediate())
        .map(|msg| match msg {
            FrameMsg::Content(VerticalMenuChoiceMsg::Selected(i)) => Some(FlowMsg::Choice(i)),
            FrameMsg::Button(_) => Some(FlowMsg::Cancelled),
        });

        let paragraphs_fingerprint =
            Paragraphs::new(Paragraph::new(&theme::TEXT_MONO_GREY_LIGHT, fingerprint));
        let content_fingerprint = Frame::left_aligned(
            TR::firmware_update__title_fingerprint.into(),
            SwipeContent::new(paragraphs_fingerprint),
        )
        .with_cancel_button()
        .with_swipe(SwipeDirection::Right, SwipeSettings::default())
        .map(|msg| {
            matches!(msg, FrameMsg::Button(CancelInfoConfirmMsg::Cancelled))
                .then_some(FlowMsg::Cancelled)
        });

        let content_confirm = Frame::left_aligned(
            TR::firmware_update__title.into(),
            SwipeContent::new(PromptScreen::new_hold_to_confirm()),
        )
        .with_menu_button()
        .with_footer(TR::instructions__hold_to_confirm.into(), None)
        .with_swipe(SwipeDirection::Down, SwipeSettings::default())
        .with_swipe(SwipeDirection::Left, SwipeSettings::default())
        .map(|msg| match msg {
            FrameMsg::Content(()) => Some(FlowMsg::Confirmed),
            FrameMsg::Button(_) => Some(FlowMsg::Info),
        });

        let res = SwipeFlow::new(&ConfirmFirmwareUpdate::Intro)?
            .with_page(&ConfirmFirmwareUpdate::Intro, content_intro)?
            .with_page(&ConfirmFirmwareUpdate::Menu, content_menu)?
            .with_page(&ConfirmFirmwareUpdate::Fingerprint, content_fingerprint)?
            .with_page(&ConfirmFirmwareUpdate::Confirm, content_confirm)?;
        Ok(LayoutObj::new(res)?.into())
    }
}
