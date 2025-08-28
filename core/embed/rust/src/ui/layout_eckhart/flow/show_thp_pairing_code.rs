use crate::{
    error,
    strutil::TString,
    translations::TR,
    ui::{
        component::{
            text::{layout::Chunks, op::OpTextLayout},
            ComponentExt, FormattedText,
        },
        flow::{
            base::{Decision, DecisionBuilder as _},
            FlowController, FlowMsg, SwipeFlow,
        },
        geometry::Direction,
    },
};

use super::super::{
    component::Button,
    constant::SCREEN,
    firmware::{
        Header, ShortMenuVec, TextScreen, TextScreenMsg, VerticalMenu, VerticalMenuScreen,
        VerticalMenuScreenMsg,
    },
    fonts, theme,
};

#[derive(Copy, Clone, PartialEq, Eq)]
pub enum ShowPairingCode {
    Main,
    Menu,
}

impl FlowController for ShowPairingCode {
    #[inline]
    fn index(&'static self) -> usize {
        *self as usize
    }

    fn handle_swipe(&'static self, _direction: Direction) -> Decision {
        self.do_nothing()
    }

    fn handle_event(&'static self, msg: FlowMsg) -> Decision {
        match (self, msg) {
            (Self::Main, FlowMsg::Cancelled) => self.return_msg(FlowMsg::Cancelled),
            (Self::Main, FlowMsg::Confirmed) => self.return_msg(FlowMsg::Confirmed),
            (Self::Main, FlowMsg::Info) => Self::Menu.goto(),
            (Self::Menu, FlowMsg::Choice(..)) => self.return_msg(FlowMsg::Cancelled),
            (Self::Menu, FlowMsg::Cancelled) => Self::Main.goto(),
            _ => self.do_nothing(),
        }
    }
}

pub fn new_show_thp_pairing_code(
    title: TString<'static>,
    description: TString<'static>,
    code: TString<'static>,
) -> Result<SwipeFlow, error::Error> {
    let available_width = SCREEN.width() - 2 * theme::PADDING;
    // Choose the font so the code fits on one line
    let (code_font, code_width) = code.map(|c| {
        let f72 = fonts::FONT_SATOSHI_EXTRALIGHT_72;
        let f46 = fonts::FONT_SATOSHI_EXTRALIGHT_46;
        if f72.text_width(c) < available_width {
            (f72, f72.text_width(c))
        } else {
            (f46, f46.text_width(c))
        }
    });
    // Adapt the offset so the code spreads accross the available width
    let x_offset = (available_width - code_width) / (code.len() as i16 - 1);

    let mut ops = OpTextLayout::new(theme::firmware::TEXT_REGULAR);
    ops.add_text(description, fonts::FONT_SATOSHI_REGULAR_38)
        .add_chunkify_text(Some((Chunks::new(1, x_offset), 70)))
        .add_color(theme::GREY_EXTRA_LIGHT)
        .add_newline()
        .add_text(code, code_font);

    let screen =
        TextScreen::new(FormattedText::new(ops)).with_header(Header::new(title).with_menu_button());
    let main_content = screen.map(|msg| match msg {
        TextScreenMsg::Cancelled => Some(FlowMsg::Cancelled),
        TextScreenMsg::Confirmed => Some(FlowMsg::Confirmed),
        TextScreenMsg::Menu => Some(FlowMsg::Info),
    });

    let mut menu = VerticalMenu::<ShortMenuVec>::empty();
    menu.item(Button::new_menu_item(
        TR::buttons__cancel.into(),
        theme::menu_item_title_orange(),
    ));

    let menu_content = VerticalMenuScreen::new(menu)
        .with_header(Header::new(TString::empty()).with_close_button())
        .map(move |msg| match msg {
            VerticalMenuScreenMsg::Selected(i) => Some(FlowMsg::Choice(i)),
            VerticalMenuScreenMsg::Close => Some(FlowMsg::Cancelled),
            _ => None,
        });

    let mut flow = SwipeFlow::new(&ShowPairingCode::Main)?;
    flow.add_page(&ShowPairingCode::Main, main_content)?
        .add_page(&ShowPairingCode::Menu, menu_content)?;

    Ok(flow)
}
