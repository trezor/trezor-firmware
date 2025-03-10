use crate::{
    strutil::TString,
    ui::{
        component::{Component, Event, EventCtx, Label},
        geometry::{Alignment, Insets, Rect},
        shape::Renderer,
        ui_firmware::MAX_WORD_QUIZ_ITEMS,
    },
};

use super::super::{
    component::Button,
    constant::SCREEN,
    firmware::{Header, HeaderMsg, VerticalMenu, VerticalMenuMsg},
    theme,
};

pub struct SelectWordScreen {
    header: Header,
    description: Label<'static>,
    menu: VerticalMenu,
}

pub enum SelectWordMsg {
    Selected(usize),
    /// Right header button clicked
    Cancelled,
}

impl SelectWordScreen {
    const DESCRIPTION_HEIGHT: i16 = 58;
    const MENU_HEIGHT: i16 = 360;
    const DESCRIPTION_PADDING: i16 = 24;
    const MENU_PADDING: i16 = 12;
    pub fn new(
        share_words_vec: [TString<'static>; MAX_WORD_QUIZ_ITEMS],
        description: TString<'static>,
    ) -> Self {
        let mut menu = VerticalMenu::empty().with_separators().with_fit_area();

        for word in share_words_vec {
            menu = menu.item(
                Button::with_text(word)
                    .styled(theme::button_select_word())
                    .with_radius(12),
            );
        }

        Self {
            header: Header::new(TString::empty()),
            description: Label::new(description, Alignment::Start, theme::TEXT_MEDIUM)
                .top_aligned(),
            menu,
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

        let description_area = description_area.inset(Insets::sides(Self::DESCRIPTION_PADDING));
        let menu_area = menu_area.inset(Insets::sides(Self::MENU_PADDING));

        self.menu.place(menu_area);
        self.description.place(description_area);
        self.header.place(header_area);

        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if let Some(HeaderMsg::Cancelled) = self.header.event(ctx, event) {
            return Some(SelectWordMsg::Cancelled);
        }

        if let Some(VerticalMenuMsg::Selected(i)) = self.menu.event(ctx, event) {
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

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for SelectWordScreen {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("SelectWordScreen");
    }
}

#[cfg(test)]
mod tests {
    use super::{super::super::constant::SCREEN, *};

    #[test]
    fn test_component_heights_fit_screen() {
        assert!(
            SelectWordScreen::DESCRIPTION_HEIGHT
                + SelectWordScreen::MENU_HEIGHT
                + Header::HEADER_HEIGHT
                <= SCREEN.height(),
            "Components overflow the screen height",
        );
    }
}
