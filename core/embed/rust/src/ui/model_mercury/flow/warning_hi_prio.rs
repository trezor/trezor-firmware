use crate::{
    error,
    micropython::qstr::Qstr,
    strutil::TString,
    translations::TR,
    ui::{
        component::{
            text::paragraphs::{Paragraph, ParagraphSource},
            ComponentExt, SwipeDirection,
        },
        flow::{base::Decision, flow_store, FlowMsg, FlowState, FlowStore, SwipeFlow},
    },
};

use super::super::{
    component::{Frame, FrameMsg, StatusScreen, VerticalMenu, VerticalMenuChoiceMsg},
    theme,
};

#[derive(Copy, Clone, PartialEq, Eq, ToPrimitive)]
pub enum WarningHiPrio {
    Message,
    Menu,
    Cancelled,
}

impl FlowState for WarningHiPrio {
    fn handle_swipe(&self, direction: SwipeDirection) -> Decision<Self> {
        let attach = AttachType::Swipe(direction);
        match (self, direction) {
            (WarningHiPrio::Message, SwipeDirection::Left) => {
                Decision::Goto(WarningHiPrio::Menu, attach)
            }
            (WarningHiPrio::Message, SwipeDirection::Up) => {
                Decision::Goto(WarningHiPrio::Cancelled, attach)
            }
            (WarningHiPrio::Menu, SwipeDirection::Right) => {
                Decision::Goto(WarningHiPrio::Message, attach)
            }
            _ => Decision::Nothing,
        }
    }

    fn handle_event(&self, msg: FlowMsg) -> Decision<Self> {
        match (self, msg) {
            (WarningHiPrio::Message, FlowMsg::Info) => {
                Decision::Goto(WarningHiPrio::Menu, AttachType::Initial)
            }
            (WarningHiPrio::Menu, FlowMsg::Choice(1)) => Decision::Return(FlowMsg::Confirmed),
            (WarningHiPrio::Menu, FlowMsg::Choice(_)) => Decision::Goto(
                WarningHiPrio::Cancelled,
                AttachType::Swipe(SwipeDirection::Up),
            ),
            (WarningHiPrio::Menu, FlowMsg::Cancelled) => Decision::Goto(
                WarningHiPrio::Message,
                AttachType::Swipe(SwipeDirection::Right),
            ),
            (WarningHiPrio::Cancelled, _) => Decision::Return(FlowMsg::Cancelled),
            _ => Decision::Nothing,
        }
    }
}

use crate::{
    micropython::{map::Map, obj::Obj, util},
    ui::{
        component::{base::AttachType, swipe_detect::SwipeSettings},
        layout::obj::LayoutObj,
        model_mercury::component::SwipeContent,
    },
};

#[allow(clippy::not_unsafe_ptr_arg_deref)]
pub extern "C" fn new_warning_hi_prio(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, WarningHiPrio::new_obj) }
}

impl WarningHiPrio {
    const EXTRA_PADDING: i16 = 6;

    fn new_obj(_args: &[Obj], kwargs: &Map) -> Result<Obj, error::Error> {
        let title: TString = kwargs.get_or(Qstr::MP_QSTR_title, TR::words__warning.into())?;
        let description: TString = kwargs.get(Qstr::MP_QSTR_description)?.try_into()?;
        let value: TString = kwargs.get_or(Qstr::MP_QSTR_value, "".into())?;
        let cancel: TString = TR::words__cancel_and_exit.into();
        let confirm: TString = "Continue anyway".into(); // FIXME: en.json has punctuation
        let done_title: TString = "Operation cancelled".into();

        // Message
        let paragraphs = [
            Paragraph::new(&theme::TEXT_MAIN_GREY_LIGHT, description),
            Paragraph::new(&theme::TEXT_MAIN_GREY_EXTRA_LIGHT, value)
                .with_top_padding(Self::EXTRA_PADDING),
        ]
        .into_paragraphs();
        let content_message = Frame::left_aligned(title, SwipeContent::new(paragraphs))
            .with_menu_button()
            .with_footer(TR::instructions__swipe_up.into(), Some(cancel))
            .with_danger()
            .with_swipe(SwipeDirection::Up, SwipeSettings::default())
            .with_swipe(SwipeDirection::Left, SwipeSettings::default())
            .map(|msg| matches!(msg, FrameMsg::Button(_)).then_some(FlowMsg::Info));
        // .one_button_request(ButtonRequestCode::Warning, br_type);

        // Menu
        let content_menu = Frame::left_aligned(
            "".into(),
            VerticalMenu::empty()
                .item(theme::ICON_CANCEL, "Cancel".into()) // TODO: button__cancel after it's lowercase
                .danger(theme::ICON_CHEVRON_RIGHT, confirm),
        )
        .with_cancel_button()
        .with_swipe(SwipeDirection::Right, SwipeSettings::immediate())
        .map(|msg| match msg {
            FrameMsg::Content(VerticalMenuChoiceMsg::Selected(i)) => Some(FlowMsg::Choice(i)),
            FrameMsg::Button(_) => Some(FlowMsg::Cancelled),
        });

        // Cancelled
        let content_cancelled =
            Frame::left_aligned(done_title, StatusScreen::new_neutral_timeout())
                .with_footer(TR::instructions__continue_in_app.into(), None)
                .map(|_| Some(FlowMsg::Cancelled));

        let store = flow_store()
            .add(content_message)?
            .add(content_menu)?
            .add(content_cancelled)?;
        let res = SwipeFlow::new(WarningHiPrio::Message, store)?;
        Ok(LayoutObj::new(res)?.into())
    }
}
