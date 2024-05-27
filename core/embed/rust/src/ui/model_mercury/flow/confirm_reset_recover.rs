use crate::{
    error,
    translations::TR,
    ui::{
        button_request::ButtonRequestCode,
        component::{
            text::paragraphs::{Paragraph, Paragraphs},
            ButtonRequestExt, ComponentExt, SwipeDirection,
        },
        flow::{base::Decision, flow_store, FlowMsg, FlowState, FlowStore, SwipeFlow, SwipePage},
    },
};

use super::super::{
    component::{Frame, FrameMsg, PromptScreen, VerticalMenu, VerticalMenuChoiceMsg},
    theme,
};

#[derive(Copy, Clone, PartialEq, Eq, ToPrimitive)]
pub enum ConfirmResetRecover {
    Intro,
    Menu,
}

impl FlowState for ConfirmResetRecover {
    fn handle_swipe(&self, direction: SwipeDirection) -> Decision<Self> {
        match (self, direction) {
            (ConfirmResetRecover::Intro, SwipeDirection::Left) => {
                Decision::Goto(ConfirmResetRecover::Menu, direction)
            }
            (ConfirmResetRecover::Menu, SwipeDirection::Right) => {
                Decision::Goto(ConfirmResetRecover::Intro, direction)
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
                Decision::Goto(ConfirmResetRecover::Menu, SwipeDirection::Left)
            }
            (ConfirmResetRecover::Menu, FlowMsg::Cancelled) => {
                Decision::Goto(ConfirmResetRecover::Intro, SwipeDirection::Right)
            }
            (ConfirmResetRecover::Menu, FlowMsg::Choice(0)) => Decision::Return(FlowMsg::Cancelled),
            _ => Decision::Nothing,
        }
    }
}

use crate::{
    micropython::{map::Map, obj::Obj, util},
    ui::layout::obj::LayoutObj,
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
            SwipePage::vertical(paragraphs),
        )
        .with_menu_button()
        .with_footer(TR::instructions__swipe_up.into(), None)
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
        .map(|msg| match msg {
            FrameMsg::Content(VerticalMenuChoiceMsg::Selected(i)) => Some(FlowMsg::Choice(i)),
            FrameMsg::Button(_) => Some(FlowMsg::Cancelled),
        });

        let content_confirm = Frame::left_aligned(
            TR::reset__title_create_wallet.into(),
            PromptScreen::new_hold_to_confirm(),
        )
        .with_footer(TR::instructions__hold_to_confirm.into(), None)
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
