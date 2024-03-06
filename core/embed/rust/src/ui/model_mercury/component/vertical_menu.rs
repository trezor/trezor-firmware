use heapless::Vec;

use super::theme;
use crate::ui::{
    component::{base::Component, Event, EventCtx},
    display::Icon,
    geometry::Rect,
    model_mercury::component::button::{Button, IconText},
    shape::{Bar, Renderer},
};

pub enum VerticalMenuChoiceMsg {
    Selected(usize),
}

type VerticalMenuButtons<T> = Vec<Button<T>, 3>;

/// fixed height of each menu button
const MENU_BUTTON_HEIGHT: i16 = 64;
/// fixed height of a bar separating buttons
const MENU_SEPARATOR_HEIGHT: i16 = 2;

pub struct VerticalMenu<T> {
    area: Rect,
    buttons: VerticalMenuButtons<T>,
    /// area for a separator between 1st and 2nd button
    area_sep1: Rect,
    /// area for a separator between 2nd and 3rd button
    area_sep2: Rect,
}

impl<T> VerticalMenu<T>
where
    T: AsRef<str>,
{
    fn new(buttons: VerticalMenuButtons<T>) -> Self {
        Self {
            area: Rect::zero(),
            buttons,
            area_sep1: Rect::zero(),
            area_sep2: Rect::zero(),
        }
    }
    pub fn select_word(words: [T; 3]) -> Self {
        let mut buttons_vec = VerticalMenuButtons::new();
        for (i, word) in words.into_iter().enumerate() {
            let button = Button::with_text(word).styled(theme::button_vertical_menu());
            buttons_vec.push(button);
        }
        Self::new(buttons_vec)
    }

    pub fn context_menu(options: [T; 3], icons: [Icon; 3]) -> Self {
        // TODO: this is just POC
        let mut buttons_vec = VerticalMenuButtons::new();
        let [opt1, opt2, opt3] = options;
        let [icon1, icon2, icon3] = icons;

        buttons_vec.push(
            Button::with_icon_and_text(IconText::new(opt1, icon1))
                .styled(theme::button_vertical_menu()),
        );
        buttons_vec.push(
            Button::with_icon_and_text(IconText::new(opt2, icon2))
                .styled(theme::button_vertical_menu()),
        );

        buttons_vec.push(
            Button::with_icon_and_text(IconText::new(opt3, icon3))
                .styled(theme::button_vertical_menu_orange()),
        );
        Self::new(buttons_vec)
    }
}

impl<T> Component for VerticalMenu<T>
where
    T: AsRef<str>,
{
    type Msg = VerticalMenuChoiceMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        // VerticalMenu is supposed to be used in Frame, the remaining space is just
        // enought to fit 3 buttons separated by thin bars
        let height_bounds_expected = 3 * MENU_BUTTON_HEIGHT + 2 * MENU_SEPARATOR_HEIGHT;
        assert!(bounds.height() == height_bounds_expected);

        self.area = bounds;
        let (area_button0, rest) = bounds.split_top(MENU_BUTTON_HEIGHT);
        self.buttons[0].place(area_button0);
        let (area_sep1, rest) = rest.split_top(MENU_SEPARATOR_HEIGHT);
        self.area_sep1 = area_sep1;
        let (area_button1, rest) = rest.split_top(MENU_BUTTON_HEIGHT);
        self.buttons[1].place(area_button1);
        let (area_sep2, rest) = rest.split_top(MENU_SEPARATOR_HEIGHT);
        self.area_sep2 = area_sep2;
        let (area_button2, _) = rest.split_top(MENU_BUTTON_HEIGHT);
        self.buttons[2].place(area_button2);
        self.area
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if let Some(btnMsg) = self.buttons[0].event(ctx, event) {
            Some(VerticalMenuChoiceMsg::Selected(0))
        } else if let Some(btnMsg) = self.buttons[1].event(ctx, event) {
            Some(VerticalMenuChoiceMsg::Selected(1))
        } else if let Some(btnMsg) = self.buttons[2].event(ctx, event) {
            Some(VerticalMenuChoiceMsg::Selected(2))
        } else {
            None
        }
    }

    fn paint(&mut self) {
        // TODO remove when ui-t3t1 done
    }

    fn render(&mut self, target: &mut impl Renderer) {
        // render buttons separated by thin bars
        self.buttons[0].render(target);
        Bar::new(self.area_sep1)
            .with_thickness(MENU_SEPARATOR_HEIGHT)
            .with_fg(theme::GREY_EXTRA_DARK)
            .render(target);
        self.buttons[1].render(target);
        Bar::new(self.area_sep2)
            .with_thickness(MENU_SEPARATOR_HEIGHT)
            .with_fg(theme::GREY_EXTRA_DARK)
            .render(target);
        self.buttons[2].render(target);
    }

    #[cfg(feature = "ui_bounds")]
    fn bounds(&self, sink: &mut dyn FnMut(Rect)) {
        sink(self.area);
    }
}

#[cfg(feature = "ui_debug")]
impl<T> crate::trace::Trace for VerticalMenu<T>
where
    T: AsRef<str>,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        // TODO: implement
        t.component("VerticalMenu");
        // t.child("inner", &self.inner);
    }
}
