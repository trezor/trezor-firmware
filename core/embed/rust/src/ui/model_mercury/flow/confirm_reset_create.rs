use crate::{
    error,
    micropython::{map::Map, obj::Obj, util},
    strutil::TString,
    translations::TR,
    ui::{
        button_request::ButtonRequestCode,
        component::{
            base::AttachType,
            swipe_detect::SwipeSettings,
            text::paragraphs::{Paragraph, Paragraphs},
            ButtonRequestExt, ComponentExt, SwipeDirection,
        },
        flow::{base::Decision, flow_store, FlowMsg, FlowState, FlowStore, SwipeFlow},
        layout::obj::LayoutObj,
        model_mercury::component::{PromptScreen, SwipeContent},
    },
};

use super::super::{
    component::{Frame, FrameMsg, VerticalMenu, VerticalMenuChoiceMsg},
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
        let attach = AttachType::Swipe(direction);
        match (self, direction) {
            (ConfirmResetCreate::Intro, SwipeDirection::Left) => {
                Decision::Goto(ConfirmResetCreate::Menu, attach)
            }
            (ConfirmResetCreate::Intro, SwipeDirection::Up) => {
                Decision::Goto(ConfirmResetCreate::Confirm, attach)
            }
            (ConfirmResetCreate::Menu, SwipeDirection::Right) => {
                Decision::Goto(ConfirmResetCreate::Intro, attach)
            }
            (ConfirmResetCreate::Confirm, SwipeDirection::Down) => {
                Decision::Goto(ConfirmResetCreate::Intro, attach)
            }
            (ConfirmResetCreate::Confirm, SwipeDirection::Left) => {
                Decision::Goto(ConfirmResetCreate::Menu, attach)
            }
            _ => Decision::Nothing,
        }
    }

    fn handle_event(&self, msg: FlowMsg) -> Decision<Self> {
        match (self, msg) {
            (ConfirmResetCreate::Intro, FlowMsg::Info) => {
                Decision::Goto(ConfirmResetCreate::Menu, AttachType::Initial)
            }
            (ConfirmResetCreate::Menu, FlowMsg::Cancelled) => Decision::Goto(
                ConfirmResetCreate::Intro,
                AttachType::Swipe(SwipeDirection::Right),
            ),
            (ConfirmResetCreate::Menu, FlowMsg::Choice(0)) => Decision::Return(FlowMsg::Cancelled),
            (ConfirmResetCreate::Confirm, FlowMsg::Confirmed) => {
                Decision::Return(FlowMsg::Confirmed)
            }
            (ConfirmResetCreate::Confirm, FlowMsg::Info) => {
                Decision::Goto(ConfirmResetCreate::Menu, AttachType::Initial)
            }
            _ => Decision::Nothing,
        }
    }
}

#[allow(clippy::not_unsafe_ptr_arg_deref)]
pub extern "C" fn new_confirm_reset_create(
    n_args: usize,
    args: *const Obj,
    kwargs: *mut Map,
) -> Obj {
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, ConfirmResetCreate::new_obj) }
}

impl ConfirmResetCreate {
    fn new_obj(_args: &[Obj], _kwargs: &Map) -> Result<Obj, error::Error> {
        let title: TString = TR::reset__title_create_wallet.into();
        let par_array: [Paragraph<'static>; 3] = [
            Paragraph::new(&theme::TEXT_MAIN_GREY_LIGHT, TR::reset__by_continuing)
                .with_bottom_padding(17),
            Paragraph::new(&theme::TEXT_SUB_GREY, TR::reset__more_info_at),
            Paragraph::new(&theme::TEXT_SUB_GREY_LIGHT, TR::reset__tos_link),
        ];
        let paragraphs = Paragraphs::new(par_array);
        let content_intro = Frame::left_aligned(title, SwipeContent::new(paragraphs))
            .with_menu_button()
            .with_footer(TR::instructions__swipe_up.into(), None)
            .with_swipe(SwipeDirection::Up, SwipeSettings::default())
            .with_swipe(SwipeDirection::Left, SwipeSettings::default())
            .map(|msg| matches!(msg, FrameMsg::Button(_)).then_some(FlowMsg::Info))
            .one_button_request(ButtonRequestCode::ResetDevice.with_type("setup_device"));

        // FIXME: TR::reset__cancel_create_wallet should be used but Button text on
        // multiple lines not supported yet
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

        let content_confirm = Frame::left_aligned(
            TR::reset__title_create_wallet.into(),
            SwipeContent::new(PromptScreen::new_hold_to_confirm()),
        )
        .with_menu_button()
        .with_footer(TR::instructions__hold_to_confirm.into(), None)
        .with_swipe(SwipeDirection::Down, SwipeSettings::default())
        .with_swipe(SwipeDirection::Left, SwipeSettings::default())
        .map(|msg| match msg {
            FrameMsg::Content(()) => Some(FlowMsg::Confirmed),
            FrameMsg::Button(_) => Some(FlowMsg::Info),
        })
        .one_button_request(ButtonRequestCode::ResetDevice.with_type("confirm_setup_device"));

        let store = flow_store()
            .add(content_intro)?
            .add(content_menu)?
            .add(content_confirm)?;

        let res = SwipeFlow::new(ConfirmResetCreate::Intro, store)?;
        Ok(LayoutObj::new(res)?.into())
    }
}
