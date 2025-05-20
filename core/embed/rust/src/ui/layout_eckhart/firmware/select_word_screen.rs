use heapless::Vec;

use crate::{
    strutil::TString,
    ui::{
        component::{Component, Event, EventCtx, Label},
        geometry::{Alignment, Insets, Offset, Rect},
        shape,
        shape::Renderer,
        ui_firmware::MAX_WORD_QUIZ_ITEMS,
    },
};

use super::super::{
    component::{Button, ButtonMsg},
    constant::SCREEN,
    firmware::{Header, HeaderMsg},
    theme,
};

pub struct SelectWordScreen {
    header: Header,
    description: Label<'static>,
    menu: SelectWordButtons,
}

pub enum SelectWordMsg {
    Selected(usize),
    /// Right header button clicked
    Cancelled,
}

impl SelectWordScreen {
    const DESCRIPTION_HEIGHT: i16 = 76;
    const MENU_HEIGHT: i16 = 330;
    const MENU_INSETS: Insets = Insets::sides(12);
    pub fn new(
        share_words_vec: [TString<'static>; MAX_WORD_QUIZ_ITEMS],
        description: TString<'static>,
    ) -> Self {
        Self {
            header: Header::new(TString::empty()),
            description: Label::new(description, Alignment::Start, theme::TEXT_MEDIUM)
                .top_aligned(),
            menu: SelectWordButtons::new(share_words_vec),
        }
    }

    pub fn with_header(mut self, header: Header) -> Self {
        self.header = header;
        self
    }
}

impl Component for SelectWordScreen {
    type Msg = SelectWordMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        // assert full screen
        debug_assert_eq!(bounds.height(), SCREEN.height());
        debug_assert_eq!(bounds.width(), SCREEN.width());

        let (header_area, rest) = bounds.split_top(Header::HEADER_HEIGHT);
        let (description_area, rest) = rest.split_top(Self::DESCRIPTION_HEIGHT);
        let (menu_area, _) = rest.split_top(Self::MENU_HEIGHT);

        self.menu.place(menu_area.inset(Self::MENU_INSETS));
        self.description
            .place(description_area.inset(theme::SIDE_INSETS));
        self.header.place(header_area);

        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if let Some(HeaderMsg::Cancelled) = self.header.event(ctx, event) {
            return Some(SelectWordMsg::Cancelled);
        }

        if let Some(i) = self.menu.event(ctx, event) {
            return Some(SelectWordMsg::Selected(i));
        }

        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.header.render(target);
        self.description.render(target);
        self.menu.render(target);
    }
}

struct SelectWordButtons {
    buttons: Vec<Button, MAX_WORD_QUIZ_ITEMS>,
}

impl SelectWordButtons {
    const SEPARATOR_PADDING: i16 = 12;
    fn new(share_words_vec: [TString<'static>; MAX_WORD_QUIZ_ITEMS]) -> Self {
        let mut buttons = Vec::new();
        for word in share_words_vec {
            unwrap!(buttons.push(
                Button::with_text(word)
                    .styled(theme::button_select_word())
                    .with_radius(12)
                    .with_text_align(Alignment::Center),
            ));
        }
        Self { buttons }
    }

    fn render_separators<'s>(&'s self, target: &mut impl Renderer<'s>) {
        for i in 1..self.buttons.len() {
            let button = &self.buttons[i];
            let button_prev = &self.buttons[i - 1];

            if !button.is_pressed() && !button_prev.is_pressed() {
                let separator = Rect::from_top_left_and_size(
                    button
                        .area()
                        .top_left()
                        .ofs(Offset::x(Self::SEPARATOR_PADDING)),
                    Offset::new(button.area().width() - 2 * Self::SEPARATOR_PADDING, 1),
                );
                shape::Bar::new(separator)
                    .with_fg(theme::GREY_EXTRA_DARK)
                    .render(target);
            }
        }
    }
}

impl Component for SelectWordButtons {
    type Msg = usize;

    fn place(&mut self, bounds: Rect) -> Rect {
        let button_height = bounds.height() / self.buttons.len() as i16;
        for (i, button) in self.buttons.iter_mut().enumerate() {
            let top_left = bounds.top_left().ofs(Offset::y(i as i16 * button_height));
            let button_bounds =
                Rect::from_top_left_and_size(top_left, Offset::new(bounds.width(), button_height));
            button.place(button_bounds);
        }

        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        for (i, button) in self.buttons.iter_mut().enumerate() {
            if let Some(ButtonMsg::Clicked) = button.event(ctx, event) {
                return Some(i);
            }
        }

        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        for button in &self.buttons {
            button.render(target);
        }
        self.render_separators(target);
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for SelectWordScreen {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("SelectWordScreen");
        t.child("Header", &self.header);
        t.child("subtitle", &self.description);
        t.in_list("buttons", &|button_list| {
            for button in &self.menu.buttons {
                button_list.child(button);
            }
        });
    }
}

#[cfg(test)]
mod tests {
    use super::{super::super::constant::SCREEN, *};

    #[test]
    fn test_component_heights_fit_screen() {
        assert!(
            Header::HEADER_HEIGHT
                + SelectWordScreen::DESCRIPTION_HEIGHT
                + SelectWordScreen::MENU_HEIGHT
                <= SCREEN.height(),
            "Components overflow the screen height",
        );
    }
}
