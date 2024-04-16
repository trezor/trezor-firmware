use crate::{
    error,
    micropython::qstr::Qstr,
    strutil::TString,
    translations::TR,
    ui::{
        component::text::paragraphs::{Paragraph, Paragraphs},
        flow::{
            base::Decision, flow_store, FlowMsg, FlowState, FlowStore, SwipeDirection, SwipeFlow,
            SwipePage,
        },
    },
};
use heapless::Vec;

use super::super::{
    component::{Frame, FrameMsg, VerticalMenu, VerticalMenuChoiceMsg},
    theme,
};

#[derive(Copy, Clone, PartialEq, Eq, ToPrimitive)]
pub enum ConfirmResetDevice {
    Intro,
    Menu,
}

impl FlowState for ConfirmResetDevice {
    fn handle_swipe(&self, direction: SwipeDirection) -> Decision<Self> {
        match (self, direction) {
            (ConfirmResetDevice::Intro, SwipeDirection::Left) => {
                Decision::Goto(ConfirmResetDevice::Menu, direction)
            }
            (ConfirmResetDevice::Menu, SwipeDirection::Right) => {
                Decision::Goto(ConfirmResetDevice::Intro, direction)
            }
            (ConfirmResetDevice::Intro, SwipeDirection::Up) => Decision::Return(FlowMsg::Confirmed),
            _ => Decision::Nothing,
        }
    }

    fn handle_event(&self, msg: FlowMsg) -> Decision<Self> {
        match (self, msg) {
            (ConfirmResetDevice::Intro, FlowMsg::Info) => {
                Decision::Goto(ConfirmResetDevice::Menu, SwipeDirection::Left)
            }
            (ConfirmResetDevice::Menu, FlowMsg::Cancelled) => {
                Decision::Goto(ConfirmResetDevice::Intro, SwipeDirection::Right)
            }
            (ConfirmResetDevice::Menu, FlowMsg::Choice(0)) => Decision::Return(FlowMsg::Cancelled),
            _ => Decision::Nothing,
        }
    }
}

use crate::{
    micropython::{buffer::StrBuffer, map::Map, obj::Obj, util},
    ui::layout::obj::LayoutObj,
};

pub extern "C" fn new_confirm_reset_device(
    n_args: usize,
    args: *const Obj,
    kwargs: *mut Map,
) -> Obj {
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, ConfirmResetDevice::new) }
}

impl ConfirmResetDevice {
    fn new(_args: &[Obj], kwargs: &Map) -> Result<Obj, error::Error> {
        let title: TString = kwargs.get(Qstr::MP_QSTR_title)?.try_into()?;
        let par_array: [Paragraph<'static>; 3] = [
            Paragraph::new(&theme::TEXT_MAIN_GREY_LIGHT, TR::reset__by_continuing)
                .with_bottom_padding(17),
            Paragraph::new(&theme::TEXT_SUB_GREY, TR::reset__more_info_at),
            Paragraph::new(&theme::TEXT_SUB_GREY_LIGHT, TR::reset__tos_link),
        ];
        let paragraphs = Paragraphs::new(par_array);
        let content_intro = Frame::left_aligned(title, SwipePage::vertical(paragraphs))
            .with_menu_button()
            .with_footer(TR::instructions__swipe_up.into(), None);

        let content_menu = Frame::left_aligned(
            "".into(),
            VerticalMenu::context_menu(unwrap!(Vec::from_slice(&[(
                "Cancel", // FIXME: use TString
                theme::ICON_CANCEL
            )]))),
        )
        .with_cancel_button();

        let content_confirm = Frame::left_aligned(
            TR::reset__title_create_wallet.into(),
            PromptScreen::new_hold_to_confirm(),
        )
        .with_footer(TR::instructions__hold_to_confirm.into(), None);

        let store = flow_store()
            // Intro,
            .add(
                Frame::left_aligned(title, SwipePage::vertical(paragraphs))
                    .with_info_button()
                    .with_footer(TR::instructions__swipe_up.into(), None),
                |msg| matches!(msg, FrameMsg::Button(_)).then_some(FlowMsg::Info),
            )?
            // Menu,
            .add(
                Frame::left_aligned(
                    "".into(),
                    VerticalMenu::context_menu(unwrap!(Vec::from_slice(&[(
                        "Cancel", // FIXME: use TString
                        theme::ICON_CANCEL
                    )]))),
                )
                .with_cancel_button(),
                |msg| match msg {
                    FrameMsg::Content(VerticalMenuChoiceMsg::Selected(i)) => {
                        Some(FlowMsg::Choice(i))
                    }
                    FrameMsg::Button(_) => Some(FlowMsg::Cancelled),
                },
            )?;

        let res = SwipeFlow::new(ConfirmResetDevice::Intro, store)?;
        Ok(LayoutObj::new(res)?.into())
    }
}
