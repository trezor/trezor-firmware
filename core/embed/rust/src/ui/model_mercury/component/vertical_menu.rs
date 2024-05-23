use heapless::Vec;

use super::theme;
use crate::{
    strutil::TString,
    ui::{
        component::{base::Component, Event, EventCtx},
        display::Icon,
        geometry::Rect,
        model_mercury::component::button::{Button, ButtonMsg, IconText},
        shape::{Bar, Renderer},
    },
};

pub enum VerticalMenuChoiceMsg {
    Selected(usize),
}

/// Number of buttons.
/// Presently, VerticalMenu holds only fixed number of buttons.
/// TODO: for scrollable menu, the implementation must change.
const N_ITEMS: usize = 3;

/// Number of visual separators between buttons.
const N_SEPS: usize = N_ITEMS - 1;

/// Fixed height of each menu button.
const MENU_BUTTON_HEIGHT: i16 = 64;

/// Fixed height of a separator.
const MENU_SEP_HEIGHT: i16 = 2;

type VerticalMenuButtons = Vec<Button, N_ITEMS>;
type AreasForSeparators = Vec<Rect, N_SEPS>;

#[derive(Clone)]
pub struct VerticalMenu {
    area: Rect,
    /// buttons placed vertically from top to bottom
    buttons: VerticalMenuButtons,
    /// areas for visual separators between buttons
    areas_sep: AreasForSeparators,
}

impl VerticalMenu {
    fn new(buttons: VerticalMenuButtons) -> Self {
        Self {
            area: Rect::zero(),
            buttons,
            areas_sep: AreasForSeparators::new(),
        }
    }
    pub fn select_word(words: [TString<'static>; 3]) -> Self {
        let mut buttons_vec = VerticalMenuButtons::new();
        for word in words {
            let button = Button::with_text(word).styled(theme::button_default());
            unwrap!(buttons_vec.push(button));
        }
        Self::new(buttons_vec)
    }

    pub fn empty() -> Self {
        Self::new(VerticalMenuButtons::new())
    }

    pub fn item(mut self, icon: Icon, text: TString<'static>) -> Self {
        unwrap!(self.buttons.push(
            Button::with_icon_and_text(IconText::new(text, icon)).styled(theme::button_default())
        ));
        self
    }

    pub fn danger(mut self, icon: Icon, text: TString<'static>) -> Self {
        unwrap!(self.buttons.push(
            Button::with_icon_and_text(IconText::new(text, icon))
                .styled(theme::button_warning_high())
        ));
        self
    }
}

impl Component for VerticalMenu {
    type Msg = VerticalMenuChoiceMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        // VerticalMenu is supposed to be used in Frame, the remaining space is just
        // enought to fit 3 buttons separated by thin bars
        let height_bounds_expected = 3 * MENU_BUTTON_HEIGHT + 2 * MENU_SEP_HEIGHT;
        assert!(bounds.height() == height_bounds_expected);

        self.area = bounds;
        self.areas_sep.clear();
        let mut remaining = bounds;
        let n_seps = self.buttons.len() - 1;
        for (i, button) in self.buttons.iter_mut().enumerate() {
            let (area_button, new_remaining) = remaining.split_top(MENU_BUTTON_HEIGHT);
            button.place(area_button);
            remaining = new_remaining;
            if i < n_seps {
                let (area_sep, new_remaining) = remaining.split_top(MENU_SEP_HEIGHT);
                unwrap!(self.areas_sep.push(area_sep));
                remaining = new_remaining;
            }
        }

        self.area
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        for (i, button) in self.buttons.iter_mut().enumerate() {
            if let Some(ButtonMsg::Clicked) = button.event(ctx, event) {
                return Some(VerticalMenuChoiceMsg::Selected(i));
            }
        }
        None
    }

    fn paint(&mut self) {
        // TODO remove when ui-t3t1 done
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        // render buttons separated by thin bars
        for button in &self.buttons {
            button.render(target);
        }
        for area in self.areas_sep.iter() {
            Bar::new(*area)
                .with_thickness(MENU_SEP_HEIGHT)
                .with_fg(theme::GREY_EXTRA_DARK)
                .render(target);
        }
    }

    #[cfg(feature = "ui_bounds")]
    fn bounds(&self, sink: &mut dyn FnMut(Rect)) {
        sink(self.area);
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for VerticalMenu {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("VerticalMenu");
        t.in_list("buttons", &|button_list| {
            for button in &self.buttons {
                button_list.child(button);
            }
        });
    }
}

#[cfg(feature = "micropython")]
impl crate::ui::flow::Swipable<VerticalMenuChoiceMsg> for VerticalMenu {}
