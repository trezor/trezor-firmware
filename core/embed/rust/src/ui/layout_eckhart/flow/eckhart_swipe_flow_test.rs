use crate::{
    error,
    ui::{
        component::{text::op::OpTextLayout, ComponentExt, FormattedText},
        flow::{
            base::{Decision, DecisionBuilder as _},
            FlowController, FlowMsg, SwipeFlow,
        },
        geometry::Direction,
        layout_eckhart::{
            component::{ActionBar, Button, Header, Hint, TextScreen, TextScreenMsg},
            fonts, theme,
        },
    },
};

#[derive(Copy, Clone, PartialEq, Eq)]
pub enum EckhartSwipeFlow {
    Text1,
    Text2,
}

impl FlowController for EckhartSwipeFlow {
    #[inline]
    fn index(&'static self) -> usize {
        *self as usize
    }

    fn handle_swipe(&'static self, direction: Direction) -> Decision {
        match (self, direction) {
            _ => self.do_nothing(),
        }
    }

    fn handle_event(&'static self, msg: FlowMsg) -> Decision {
        match (self, msg) {
            (Self::Text1, FlowMsg::Cancelled) => self.return_msg(FlowMsg::Cancelled),
            (Self::Text1, FlowMsg::Confirmed) => Self::Text2.goto(),
            (Self::Text2, FlowMsg::Cancelled) => Self::Text1.goto(),
            (Self::Text2, FlowMsg::Confirmed) => self.return_msg(FlowMsg::Confirmed),
            _ => self.do_nothing(),
        }
    }
}

pub fn new_eckhart_swipe_flow() -> Result<SwipeFlow, error::Error> {
    let op1 = OpTextLayout::new(theme::TEXT_NORMAL)
        .text("Nice op text", fonts::FONT_SATOSHI_REGULAR_38)
        .newline()
        .text("Indeed nice", fonts::FONT_SATOSHI_MEDIUM_26);

    let content_text1 = TextScreen::new(FormattedText::new(op1).vertically_centered())
        .with_header(
            Header::new("Header".into())
                // .with_right_button(Button::with_icon(theme::ICON_MENU), HeaderMsg::Menu)
                .with_menu_button()
                .with_icon(theme::ICON_DONE, theme::GREEN_LIME),
        )
        .with_hint(Hint::new_instruction(
            "Nice description",
            Some(theme::ICON_INFO),
        ))
        // .with_hint(Hint::new_page_counter())
        .with_action_bar(ActionBar::new_double(
            Button::with_icon(theme::ICON_CHEVRON_LEFT),
            Button::with_text("Confirm".into()),
        ))
        .map(|msg| match msg {
            TextScreenMsg::Cancelled => Some(FlowMsg::Cancelled),
            TextScreenMsg::Confirmed => Some(FlowMsg::Confirmed),
            TextScreenMsg::Menu => todo!(),
        });

    let op2 = OpTextLayout::new(theme::TEXT_NORMAL)
        .text("Another great text", fonts::FONT_SATOSHI_REGULAR_38)
        .newline()
        .text("Indeed great", fonts::FONT_SATOSHI_MEDIUM_26);
    let content_text2 = TextScreen::new(FormattedText::new(op2).vertically_centered())
        .with_header(
            Header::new("Header".into())
                // .with_right_button(Button::with_icon(theme::ICON_MENU), HeaderMsg::Menu)
                .with_menu_button()
                .with_icon(theme::ICON_DONE, theme::GREEN_LIME),
        )
        .with_hint(Hint::new_instruction(
            "Great description",
            Some(theme::ICON_INFO),
        ))
        // .with_hint(Hint::new_page_counter())
        .with_action_bar(ActionBar::new_double(
            Button::with_icon(theme::ICON_CHEVRON_LEFT),
            Button::with_text("Confirm".into()),
        ))
        .map(|msg| match msg {
            TextScreenMsg::Cancelled => Some(FlowMsg::Cancelled),
            TextScreenMsg::Confirmed => Some(FlowMsg::Confirmed),
            TextScreenMsg::Menu => todo!(),
        });

    let res = SwipeFlow::new(&EckhartSwipeFlow::Text1)?
        .with_page(&EckhartSwipeFlow::Text1, content_text1)?
        .with_page(&EckhartSwipeFlow::Text2, content_text2)?;
    Ok(res)
}
