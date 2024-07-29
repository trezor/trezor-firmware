use crate::{
    error,
    micropython::{map::Map, obj::Obj, qstr::Qstr, util},
    strutil::TString,
    translations::TR,
    ui::{
        component::{
            swipe_detect::SwipeSettings,
            text::paragraphs::{Paragraph, ParagraphSource, ParagraphVecShort, Paragraphs},
            ComponentExt, SwipeDirection,
        },
        flow::{
            base::{DecisionBuilder as _, StateChange},
            FlowMsg, FlowState, SwipeFlow,
        },
        layout::obj::LayoutObj,
        model_mercury::component::SwipeContent,
    },
};

use super::super::{
    component::{
        CancelInfoConfirmMsg, Frame, FrameMsg, PromptScreen, VerticalMenu, VerticalMenuChoiceMsg,
    },
    theme,
};

#[derive(Copy, Clone, PartialEq, Eq)]
pub enum SetNewPin {
    Intro,
    Menu,
    CancelPinIntro,
    CancelPinConfirm,
}

impl FlowState for SetNewPin {
    #[inline]
    fn index(&'static self) -> usize {
        *self as usize
    }

    fn handle_swipe(&'static self, direction: SwipeDirection) -> StateChange {
        match (self, direction) {
            (Self::Intro, SwipeDirection::Left) => Self::Menu.swipe(direction),
            (Self::Intro, SwipeDirection::Up) => self.return_msg(FlowMsg::Confirmed),
            (Self::Menu, SwipeDirection::Right) => Self::Intro.swipe(direction),
            (Self::CancelPinIntro, SwipeDirection::Up) => Self::CancelPinConfirm.swipe(direction),
            (Self::CancelPinIntro, SwipeDirection::Right) => Self::Intro.swipe(direction),
            (Self::CancelPinConfirm, SwipeDirection::Down) => Self::CancelPinIntro.swipe(direction),
            (Self::CancelPinConfirm, SwipeDirection::Right) => Self::Intro.swipe(direction),
            _ => self.do_nothing(),
        }
    }

    fn handle_event(&'static self, msg: FlowMsg) -> StateChange {
        match (self, msg) {
            (Self::Intro, FlowMsg::Info) => Self::Menu.transit(),
            (Self::Menu, FlowMsg::Choice(0)) => Self::CancelPinIntro.swipe_left(),
            (Self::Menu, FlowMsg::Cancelled) => Self::Intro.swipe_right(),
            (Self::CancelPinIntro, FlowMsg::Cancelled) => Self::Intro.swipe_right(),
            (Self::CancelPinConfirm, FlowMsg::Cancelled) => Self::CancelPinIntro.swipe_right(),
            (Self::CancelPinConfirm, FlowMsg::Confirmed) => self.return_msg(FlowMsg::Cancelled),
            _ => self.do_nothing(),
        }
    }
}

#[allow(clippy::not_unsafe_ptr_arg_deref)]
pub extern "C" fn new_set_new_pin(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, SetNewPin::new_obj) }
}

impl SetNewPin {
    fn new_obj(_args: &[Obj], kwargs: &Map) -> Result<Obj, error::Error> {
        // TODO: supply more arguments for Wipe code setting when figma done
        let title: TString = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let description: TString = kwargs.get(Qstr::MP_QSTR_description)?.try_into()?;

        let paragraphs = Paragraphs::new(Paragraph::new(&theme::TEXT_MAIN_GREY_LIGHT, description));
        let content_intro = Frame::left_aligned(title, SwipeContent::new(paragraphs))
            .with_menu_button()
            .with_footer(TR::instructions__swipe_up.into(), None)
            .with_swipe(SwipeDirection::Up, SwipeSettings::default())
            .with_swipe(SwipeDirection::Left, SwipeSettings::default())
            .map(|msg| {
                matches!(msg, FrameMsg::Button(CancelInfoConfirmMsg::Info)).then_some(FlowMsg::Info)
            });

        let content_menu = Frame::left_aligned(
            "".into(),
            VerticalMenu::empty().danger(theme::ICON_CANCEL, TR::pin__cancel_setup.into()),
        )
        .with_cancel_button()
        .with_swipe(SwipeDirection::Right, SwipeSettings::immediate())
        .map(|msg| match msg {
            FrameMsg::Content(VerticalMenuChoiceMsg::Selected(i)) => Some(FlowMsg::Choice(i)),
            FrameMsg::Button(CancelInfoConfirmMsg::Cancelled) => Some(FlowMsg::Cancelled),
            FrameMsg::Button(_) => None,
        });

        let paragraphs_cancel_intro = ParagraphVecShort::from_iter([
            Paragraph::new(&theme::TEXT_WARNING, TR::words__not_recommended),
            Paragraph::new(&theme::TEXT_MAIN_GREY_LIGHT, TR::pin__cancel_info),
        ])
        .into_paragraphs();
        let content_cancel_intro = Frame::left_aligned(
            TR::pin__cancel_setup.into(),
            SwipeContent::new(paragraphs_cancel_intro),
        )
        .with_cancel_button()
        .with_footer(
            TR::instructions__swipe_up.into(),
            Some(TR::pin__cancel_description.into()),
        )
        .with_swipe(SwipeDirection::Up, SwipeSettings::default())
        .with_swipe(SwipeDirection::Right, SwipeSettings::immediate())
        .map(|msg| match msg {
            FrameMsg::Button(CancelInfoConfirmMsg::Cancelled) => Some(FlowMsg::Cancelled),
            _ => None,
        });

        let content_cancel_confirm = Frame::left_aligned(
            TR::pin__cancel_setup.into(),
            SwipeContent::new(PromptScreen::new_tap_to_cancel()),
        )
        .with_cancel_button()
        .with_footer(TR::instructions__tap_to_confirm.into(), None)
        .with_swipe(SwipeDirection::Down, SwipeSettings::default())
        .with_swipe(SwipeDirection::Right, SwipeSettings::immediate())
        .map(|msg| match msg {
            FrameMsg::Content(()) => Some(FlowMsg::Confirmed),
            FrameMsg::Button(CancelInfoConfirmMsg::Cancelled) => Some(FlowMsg::Cancelled),
            _ => None,
        });

        let res = SwipeFlow::new(&SetNewPin::Intro)?
            .with_page(&SetNewPin::Intro, content_intro)?
            .with_page(&SetNewPin::Menu, content_menu)?
            .with_page(&SetNewPin::CancelPinIntro, content_cancel_intro)?
            .with_page(&SetNewPin::CancelPinConfirm, content_cancel_confirm)?;
        Ok(LayoutObj::new(res)?.into())
    }
}
