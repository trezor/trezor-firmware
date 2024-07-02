use crate::{
    error,
    translations::TR,
    ui::{
        button_request::ButtonRequestCode,
        component::{
            text::paragraphs::{Paragraph, Paragraphs},
            ButtonRequestExt, ComponentExt, SwipeDirection,
        },
        flow::{base::Decision, flow_store, FlowMsg, FlowState, FlowStore, SwipeFlow},
    },
};

use super::super::{
    component::{Frame, FrameMsg, VerticalMenu, VerticalMenuChoiceMsg},
    theme,
};

#[derive(Copy, Clone, PartialEq, Eq, ToPrimitive)]
pub enum ConfirmResetRecover {
    Intro,
    Menu,
}

impl FlowState for ConfirmResetRecover {
    fn handle_swipe(&self, direction: SwipeDirection) -> Decision<Self> {
        let attach = AttachType::Swipe(direction);
        match (self, direction) {
            (ConfirmResetRecover::Intro, SwipeDirection::Left) => {
                Decision::Goto(ConfirmResetRecover::Menu, attach)
            }
            (ConfirmResetRecover::Menu, SwipeDirection::Right) => {
                Decision::Goto(ConfirmResetRecover::Intro, attach)
            }
            (ConfirmResetRecover::Intro, SwipeDirection::Up) => {
                Decision::Return(FlowMsg::Confirmed)
            }
            _ => Decision::Nothing,
        }
    }

    fn handle_event(&self, msg: FlowMsg) -> Decision<Self> {
        match (self, msg) {
            (ConfirmResetRecover::Intro, FlowMsg::Info) => {
                Decision::Goto(ConfirmResetRecover::Menu, AttachType::Initial)
            }
            (ConfirmResetRecover::Menu, FlowMsg::Cancelled) => Decision::Goto(
                ConfirmResetRecover::Intro,
                AttachType::Swipe(SwipeDirection::Right),
            ),
            (ConfirmResetRecover::Menu, FlowMsg::Choice(0)) => Decision::Return(FlowMsg::Cancelled),
            _ => Decision::Nothing,
        }
    }
}

use crate::{
    micropython::{map::Map, obj::Obj, util},
    ui::{
        component::{base::AttachType, swipe_detect::SwipeSettings},
        layout::obj::LayoutObj,
        model_mercury::component::{PromptScreen, SwipeContent},
    },
};

#[allow(clippy::not_unsafe_ptr_arg_deref)]
pub extern "C" fn new_confirm_reset_recover(
    n_args: usize,
    args: *const Obj,
    kwargs: *mut Map,
) -> Obj {
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, ConfirmResetRecover::new_obj) }
}

impl ConfirmResetRecover {
    fn new_obj(_args: &[Obj], _kwargs: &Map) -> Result<Obj, error::Error> {
        let par_array: [Paragraph<'static>; 3] = [
            Paragraph::new(&theme::TEXT_MAIN_GREY_LIGHT, TR::reset__by_continuing)
                .with_bottom_padding(17),
            Paragraph::new(&theme::TEXT_SUB_GREY, TR::reset__more_info_at),
            Paragraph::new(&theme::TEXT_SUB_GREY_LIGHT, TR::reset__tos_link),
        ];
        let paragraphs = Paragraphs::new(par_array);
        let content_intro = Frame::left_aligned(
            TR::recovery__title_recover.into(),
            SwipeContent::new(paragraphs),
        )
        .with_menu_button()
        .with_footer(TR::instructions__swipe_up.into(), None)
        .with_swipe(SwipeDirection::Up, SwipeSettings::default())
        .with_swipe(SwipeDirection::Left, SwipeSettings::default())
        .map(|msg| matches!(msg, FrameMsg::Button(_)).then_some(FlowMsg::Info))
        .one_button_request(ButtonRequestCode::ProtectCall.with_type("recover_device"));

        let content_menu = Frame::left_aligned(
            "".into(),
            VerticalMenu::empty().danger(
                theme::ICON_CANCEL,
                TR::recovery__title_cancel_recovery.into(),
            ),
        )
        .with_cancel_button()
        .with_swipe(SwipeDirection::Right, SwipeSettings::immediate())
        .map(|msg| match msg {
            FrameMsg::Content(VerticalMenuChoiceMsg::Selected(i)) => Some(FlowMsg::Choice(i)),
            FrameMsg::Button(_) => Some(FlowMsg::Cancelled),
        });

        let content_confirm = Frame::left_aligned(
            TR::reset__title_create_wallet.into(),
            SwipeContent::new(PromptScreen::new_hold_to_confirm()),
        )
        .with_footer(TR::instructions__hold_to_confirm.into(), None)
        .with_swipe(SwipeDirection::Down, SwipeSettings::default())
        .map(|msg| match msg {
            FrameMsg::Content(()) => Some(FlowMsg::Confirmed),
            _ => Some(FlowMsg::Cancelled),
        });

        let store = flow_store()
            .add(content_intro)?
            .add(content_menu)?
            .add(content_confirm)?;

        let res = SwipeFlow::new(ConfirmResetRecover::Intro, store)?;
        Ok(LayoutObj::new(res)?.into())
    }
}
