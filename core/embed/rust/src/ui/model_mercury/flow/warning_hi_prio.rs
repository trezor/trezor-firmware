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
        flow::{
            base::Decision, flow_store, FlowMsg, FlowState, FlowStore, IgnoreSwipe, SwipeFlow,
            SwipePage,
        },
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
        match (self, direction) {
            (WarningHiPrio::Message, SwipeDirection::Left) => {
                Decision::Goto(WarningHiPrio::Menu, direction)
            }
            (WarningHiPrio::Message, SwipeDirection::Up) => {
                Decision::Goto(WarningHiPrio::Cancelled, direction)
            }
            (WarningHiPrio::Menu, SwipeDirection::Right) => {
                Decision::Goto(WarningHiPrio::Message, direction)
            }
            _ => Decision::Nothing,
        }
    }

    fn handle_event(&self, msg: FlowMsg) -> Decision<Self> {
        match (self, msg) {
            (WarningHiPrio::Message, FlowMsg::Info) => {
                Decision::Goto(WarningHiPrio::Menu, SwipeDirection::Left)
            }
            (WarningHiPrio::Menu, FlowMsg::Choice(1)) => Decision::Return(FlowMsg::Confirmed),
            (WarningHiPrio::Menu, FlowMsg::Choice(_)) => {
                Decision::Goto(WarningHiPrio::Cancelled, SwipeDirection::Up)
            }
            (WarningHiPrio::Menu, FlowMsg::Cancelled) => {
                Decision::Goto(WarningHiPrio::Message, SwipeDirection::Right)
            }
            (WarningHiPrio::Cancelled, _) => Decision::Return(FlowMsg::Cancelled),
            _ => Decision::Nothing,
        }
    }
}

use crate::{
    micropython::{map::Map, obj::Obj, util},
    ui::layout::obj::LayoutObj,
};

pub extern "C" fn new_warning_hi_prio(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, WarningHiPrio::new) }
}

impl WarningHiPrio {
    const EXTRA_PADDING: i16 = 6;

    fn new(_args: &[Obj], kwargs: &Map) -> Result<Obj, error::Error> {
        let title: TString = kwargs.get_or(Qstr::MP_QSTR_title, TR::words__warning.try_into()?)?;
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
        let content_message = Frame::left_aligned(title, SwipePage::vertical(paragraphs))
            .with_menu_button()
            .with_footer(TR::instructions__swipe_up.into(), Some(cancel))
            .with_danger()
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
        .map(|msg| match msg {
            FrameMsg::Content(VerticalMenuChoiceMsg::Selected(i)) => Some(FlowMsg::Choice(i)),
            FrameMsg::Button(_) => Some(FlowMsg::Cancelled),
        });

        // Cancelled
        let content_cancelled = IgnoreSwipe::new(
            Frame::left_aligned(done_title, StatusScreen::new_neutral_timeout())
                .with_footer(TR::instructions__continue_in_app.into(), None),
        )
        .map(|_| Some(FlowMsg::Cancelled));

        let store = flow_store()
            .add(content_message)?
            .add(content_menu)?
            .add(content_cancelled)?;
        let res = SwipeFlow::new(WarningHiPrio::Message, store)?;
        Ok(LayoutObj::new(res)?.into())
    }
}
