use crate::{
    error,
    micropython::{map::Map, obj::Obj, qstr::Qstr, util},
    strutil::TString,
    translations::TR,
    ui::{
        component::{
            swipe_detect::SwipeSettings,
            text::paragraphs::{Paragraph, Paragraphs},
            ComponentExt,
        },
        flow::{
            base::{Decision, DecisionBuilder as _},
            FlowController, FlowMsg, SwipeFlow,
        },
        geometry::Direction,
        layout::obj::LayoutObj,
    },
};

use super::super::{
    component::{
        Frame, FrameMsg, PromptMsg, PromptScreen, SwipeContent, VerticalMenu, VerticalMenuChoiceMsg,
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

impl FlowController for ConfirmFirmwareUpdate {
    #[inline]
    fn index(&'static self) -> usize {
        *self as usize
    }

    fn handle_swipe(&'static self, direction: Direction) -> Decision {
        match (self, direction) {
            (Self::Intro, Direction::Left) => Self::Menu.swipe(direction),
            (Self::Intro, Direction::Up) => Self::Confirm.swipe(direction),
            (Self::Menu, Direction::Right) => Self::Intro.swipe(direction),
            (Self::Fingerprint, Direction::Right) => Self::Menu.swipe(direction),
            (Self::Confirm, Direction::Down) => Self::Intro.swipe(direction),
            (Self::Confirm, Direction::Left) => Self::Menu.swipe(direction),
            _ => self.do_nothing(),
        }
    }

    fn handle_event(&'static self, msg: FlowMsg) -> Decision {
        match (self, msg) {
            (Self::Intro, FlowMsg::Info) => Self::Menu.goto(),
            (Self::Menu, FlowMsg::Cancelled) => Self::Intro.swipe_right(),
            (Self::Menu, FlowMsg::Choice(0)) => Self::Fingerprint.goto(),
            (Self::Menu, FlowMsg::Choice(1)) => self.return_msg(FlowMsg::Cancelled),
            (Self::Fingerprint, FlowMsg::Cancelled) => Self::Menu.goto(),
            (Self::Confirm, FlowMsg::Confirmed) => self.return_msg(FlowMsg::Confirmed),
            (Self::Confirm, FlowMsg::Info) => Self::Menu.goto(),
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
        .with_swipe(Direction::Up, SwipeSettings::default())
        .with_swipe(Direction::Left, SwipeSettings::default())
        .map(|msg| matches!(msg, FrameMsg::Button(FlowMsg::Info)).then_some(FlowMsg::Info));

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
        .with_swipe(Direction::Right, SwipeSettings::immediate())
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
        .with_swipe(Direction::Right, SwipeSettings::default())
        .map(|msg| {
            matches!(msg, FrameMsg::Button(FlowMsg::Cancelled)).then_some(FlowMsg::Cancelled)
        });

        let content_confirm = Frame::left_aligned(
            TR::firmware_update__title.into(),
            SwipeContent::new(PromptScreen::new_hold_to_confirm()),
        )
        .with_menu_button()
        .with_footer(TR::instructions__hold_to_confirm.into(), None)
        .with_swipe(Direction::Down, SwipeSettings::default())
        .with_swipe(Direction::Left, SwipeSettings::default())
        .map(|msg| match msg {
            FrameMsg::Content(PromptMsg::Confirmed) => Some(FlowMsg::Confirmed),
            FrameMsg::Button(_) => Some(FlowMsg::Info),
            _ => None,
        });

        let res = SwipeFlow::new(&ConfirmFirmwareUpdate::Intro)?
            .with_page(&ConfirmFirmwareUpdate::Intro, content_intro)?
            .with_page(&ConfirmFirmwareUpdate::Menu, content_menu)?
            .with_page(&ConfirmFirmwareUpdate::Fingerprint, content_fingerprint)?
            .with_page(&ConfirmFirmwareUpdate::Confirm, content_confirm)?;
        Ok(LayoutObj::new(res)?.into())
    }
}
