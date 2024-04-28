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
        flow::{base::Decision, flow_store, FlowMsg, FlowState, FlowStore, SwipeFlow, SwipePage},
    },
};

use super::super::{
    component::{Frame, FrameMsg, PromptScreen, VerticalMenu, VerticalMenuChoiceMsg},
    theme,
};

#[derive(Copy, Clone, PartialEq, Eq, ToPrimitive)]
pub enum ConfirmResetCreate {
    Intro,
    Menu,
    Confirm,
}

impl FlowState for ConfirmResetCreate {
    fn handle_swipe(&self, direction: SwipeDirection) -> Decision<Self> {
        match (self, direction) {
            (ConfirmResetCreate::Intro, SwipeDirection::Left) => {
                Decision::Goto(ConfirmResetCreate::Menu, direction)
            }
            (ConfirmResetCreate::Menu, SwipeDirection::Right) => {
                Decision::Goto(ConfirmResetCreate::Intro, direction)
            }
            (ConfirmResetCreate::Intro, SwipeDirection::Up) => {
                Decision::Goto(ConfirmResetCreate::Confirm, direction)
            }
            (ConfirmResetCreate::Confirm, SwipeDirection::Down) => {
                Decision::Goto(ConfirmResetCreate::Intro, direction)
            }
            _ => Decision::Nothing,
        }
    }

    fn handle_event(&self, msg: FlowMsg) -> Decision<Self> {
        match (self, msg) {
            (ConfirmResetCreate::Intro, FlowMsg::Info) => {
                Decision::Goto(ConfirmResetCreate::Menu, SwipeDirection::Left)
            }
            (ConfirmResetCreate::Menu, FlowMsg::Cancelled) => {
                Decision::Goto(ConfirmResetCreate::Intro, SwipeDirection::Right)
            }
            (ConfirmResetCreate::Menu, FlowMsg::Choice(0)) => Decision::Return(FlowMsg::Cancelled),
            (ConfirmResetCreate::Confirm, FlowMsg::Confirmed) => {
                Decision::Return(FlowMsg::Confirmed)
            }
            _ => Decision::Nothing,
        }
    }
}

use crate::{
    micropython::{map::Map, obj::Obj, util},
    ui::layout::obj::LayoutObj,
};

pub extern "C" fn new_confirm_reset_create(
    n_args: usize,
    args: *const Obj,
    kwargs: *mut Map,
) -> Obj {
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, ConfirmResetCreate::new) }
}

impl ConfirmResetCreate {
    fn new(_args: &[Obj], kwargs: &Map) -> Result<Obj, error::Error> {
        let title: TString = TR::reset__title_create_wallet.into();
        let par_array: [Paragraph<'static>; 3] = [
            Paragraph::new(&theme::TEXT_MAIN_GREY_LIGHT, TR::reset__by_continuing)
                .with_bottom_padding(17),
            Paragraph::new(&theme::TEXT_SUB_GREY, TR::reset__more_info_at),
            Paragraph::new(&theme::TEXT_SUB_GREY_LIGHT, TR::reset__tos_link),
        ];
        let paragraphs = Paragraphs::new(par_array);
        let content_intro = Frame::left_aligned(title, SwipePage::vertical(paragraphs))
            .with_menu_button()
            .with_footer(TR::instructions__swipe_up.into(), None)
            .map(|msg| matches!(msg, FrameMsg::Button(_)).then_some(FlowMsg::Info));

        let content_menu = Frame::left_aligned(
            "".into(),
            VerticalMenu::empty().danger(theme::ICON_CANCEL, "Cancel".into()), // TODO: use TR
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

        let res = SwipeFlow::new(ConfirmResetCreate::Intro, store)?;
        Ok(LayoutObj::new(res)?.into())
    }
}
