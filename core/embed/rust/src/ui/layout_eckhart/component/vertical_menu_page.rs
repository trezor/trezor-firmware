use crate::{
    strutil::TString,
    ui::{
        component::{Component, Event, EventCtx},
        display::Icon,
        geometry::Rect,
        layout_eckhart::{component::button::IconText, theme},
        shape::Renderer,
    },
};

use heapless::Vec;

use super::{button::ButtonMsg, constant, Button, Header, HeaderMsg};

/// Number of buttons.
/// Presently, VerticalMenu holds only fixed number of buttons.
const MENU_MAX_ITEMS: usize = 4;

type VerticalMenuButtons = Vec<Button, MENU_MAX_ITEMS>;

/// TODO: this is just a mockup for now
pub struct VerticalMenuPage {
    header: Header,
    buttons: VerticalMenuButtons,
}

pub enum VerticalMenuMsg {
    Selected(usize),
    /// Left header button clicked
    Back,
    /// Right header button clicked
    Close,
}

impl VerticalMenuPage {
    fn new(buttons: VerticalMenuButtons) -> Self {
        Self {
            header: Header::new(TString::empty()),
            buttons,
        }
    }

    pub fn empty() -> Self {
        Self::new(VerticalMenuButtons::new())
    }

    pub fn with_header(mut self, header: Header) -> Self {
        self.header = header;
        self
    }

    pub fn item(mut self, icon: Icon, text: TString<'static>) -> Self {
        unwrap!(self.buttons.push(
            Button::with_icon_and_text(IconText::new(text, icon)).styled(theme::button_default())
        ));
        self
    }

    pub fn danger(mut self, icon: Icon, text: TString<'static>) -> Self {
        unwrap!(
            (self.buttons.push(
                Button::with_icon_and_text(IconText::new(text, icon))
                    .styled(theme::button_warning_high())
            )),
            "unwrap failed"
        );
        self
    }
}

impl Component for VerticalMenuPage {
    type Msg = VerticalMenuMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        // assert full screen
        debug_assert_eq!(bounds.height(), constant::HEIGHT);
        debug_assert_eq!(bounds.width(), constant::WIDTH);

        const MENU_BUTTON_HEIGHT: i16 = 64; // TODO: variable height buttons
        /// Fixed height of a separator.
        const MENU_SEP_HEIGHT: i16 = 2;
        let n_seps = self.buttons.len() - 1;
        let (header_area, mut rest) = bounds.split_top(Header::HEADER_HEIGHT);
        for (i, button) in self.buttons.iter_mut().enumerate() {
            let (area_button, new_remaining) = rest.split_top(MENU_BUTTON_HEIGHT);
            button.place(area_button);
            rest = new_remaining;
            if i < n_seps {
                let (_area_sep, new_remaining) = rest.split_top(MENU_SEP_HEIGHT);
                rest = new_remaining;
            }
        }

        self.header.place(header_area);

        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if let Some(msg) = self.header.event(ctx, event) {
            match msg {
                HeaderMsg::Cancelled => return Some(VerticalMenuMsg::Close),
                _ => {}
            }
        }

        for (i, button) in self.buttons.iter_mut().enumerate() {
            if let Some(ButtonMsg::Clicked) = button.event(ctx, event) {
                return Some(VerticalMenuMsg::Selected(i));
            }
        }
        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        for (i, button) in (&self.buttons).into_iter().enumerate() {
            button.render(target);
        }
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for VerticalMenuPage {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("VerticalMenuPage");
        t.in_list("buttons", &|button_list| {
            for button in &self.buttons {
                button_list.child(button);
            }
        });
    }
}
