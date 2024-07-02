use crate::{
    error,
    micropython::qstr::Qstr,
    strutil::TString,
    translations::TR,
    ui::{
        component::{
            text::paragraphs::{Paragraph, Paragraphs},
            ComponentExt, SwipeDirection,
        },
        flow::{base::Decision, FlowMsg, FlowState, FlowStore},
    },
};

use super::super::{
    component::{
        CancelInfoConfirmMsg, Frame, FrameMsg, PromptScreen, VerticalMenu, VerticalMenuChoiceMsg,
    },
    theme,
};

#[derive(Copy, Clone, PartialEq, Eq, ToPrimitive)]
pub enum SetNewPin {
    Intro,
    Menu,
    CancelPinIntro,
    CancelPinConfirm,
}

impl FlowState for SetNewPin {
    fn handle_swipe(&self, direction: SwipeDirection) -> Decision<Self> {
        let attach = AttachType::Swipe(direction);
        match (self, direction) {
            (SetNewPin::Intro, SwipeDirection::Left) => Decision::Goto(SetNewPin::Menu, attach),
            (SetNewPin::Intro, SwipeDirection::Up) => Decision::Return(FlowMsg::Confirmed),

            (SetNewPin::Menu, SwipeDirection::Right) => Decision::Goto(SetNewPin::Intro, attach),
            (SetNewPin::CancelPinIntro, SwipeDirection::Up) => {
                Decision::Goto(SetNewPin::CancelPinConfirm, attach)
            }
            (SetNewPin::CancelPinIntro, SwipeDirection::Right) => {
                Decision::Goto(SetNewPin::Intro, attach)
            }
            (SetNewPin::CancelPinConfirm, SwipeDirection::Down) => {
                Decision::Goto(SetNewPin::CancelPinIntro, attach)
            }
            (SetNewPin::CancelPinConfirm, SwipeDirection::Right) => {
                Decision::Goto(SetNewPin::Intro, attach)
            }
            _ => Decision::Nothing,
        }
    }

    fn handle_event(&self, msg: FlowMsg) -> Decision<Self> {
        match (self, msg) {
            (SetNewPin::Intro, FlowMsg::Info) => {
                Decision::Goto(SetNewPin::Menu, AttachType::Initial)
            }
            (SetNewPin::Menu, FlowMsg::Choice(0)) => Decision::Goto(
                SetNewPin::CancelPinIntro,
                AttachType::Swipe(SwipeDirection::Left),
            ),
            (SetNewPin::Menu, FlowMsg::Cancelled) => {
                Decision::Goto(SetNewPin::Intro, AttachType::Swipe(SwipeDirection::Right))
            }
            (SetNewPin::CancelPinIntro, FlowMsg::Cancelled) => {
                Decision::Goto(SetNewPin::Intro, AttachType::Swipe(SwipeDirection::Right))
            }
            (SetNewPin::CancelPinConfirm, FlowMsg::Cancelled) => Decision::Goto(
                SetNewPin::CancelPinIntro,
                AttachType::Swipe(SwipeDirection::Right),
            ),
            (SetNewPin::CancelPinConfirm, FlowMsg::Confirmed) => {
                Decision::Return(FlowMsg::Cancelled)
            }
            _ => Decision::Nothing,
        }
    }
}

use crate::{
    micropython::{map::Map, obj::Obj, util},
    ui::{
        component::{base::AttachType, swipe_detect::SwipeSettings},
        flow::{flow_store, SwipeFlow},
        layout::obj::LayoutObj,
        model_mercury::component::SwipeContent,
    },
};

#[allow(clippy::not_unsafe_ptr_arg_deref)]
pub extern "C" fn new_set_new_pin(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, SetNewPin::new_obj) }
}

impl SetNewPin {
    fn new_obj(_args: &[Obj], kwargs: &Map) -> Result<Obj, error::Error> {
        // TODO: supply more arguments for Wipe code setting when figma done
        let title: TString = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let description: TString = kwargs.get(Qstr::MP_QSTR_description)?.try_into()?;

        let par_array: [Paragraph<'static>; 1] =
            [Paragraph::new(&theme::TEXT_MAIN_GREY_LIGHT, description)];
        let paragraphs = Paragraphs::new(par_array);
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

        let par_array_cancel_intro: [Paragraph<'static>; 2] = [
            Paragraph::new(&theme::TEXT_WARNING, TR::words__not_recommended),
            Paragraph::new(&theme::TEXT_MAIN_GREY_LIGHT, TR::pin__cancel_info),
        ];
        let paragraphs_cancel_intro = Paragraphs::new(par_array_cancel_intro);
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

        let store = flow_store()
            .add(content_intro)?
            .add(content_menu)?
            .add(content_cancel_intro)?
            .add(content_cancel_confirm)?;
        let res = SwipeFlow::new(SetNewPin::Intro, store)?;
        Ok(LayoutObj::new(res)?.into())
    }
}
