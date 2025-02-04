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
    component::{Button, Header, HeaderMsg, VerticalMenu, VerticalMenuMsg},
    constant::SCREEN,
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
    const INSET: i16 = 24;
    const DESCRIPTION_HEIGHT: i16 = 52;
    const BUTTON_RADIUS: u8 = 12;

    pub fn new(
        share_words_vec: [TString<'static>; MAX_WORD_QUIZ_ITEMS],
        description: TString<'static>,
    ) -> Self {
        let mut menu = VerticalMenu::empty().with_separators().with_fit_area();

        for word in share_words_vec {
            menu = menu.item(
                Button::with_text(word)
                    .styled(theme::button_select_word())
                    .with_radius(Self::BUTTON_RADIUS),
            );
        }

        Self {
            header: Header::new(TString::empty()),
            description: Label::new(description, Alignment::Start, theme::TEXT_MEDIUM)
                .vertically_centered(),
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
        let (_, rest) = rest.split_top(Self::INSET);
        let (menu_area, _) = rest.split_bottom(Self::INSET);

        let description_area = description_area.inset(Insets::sides(Self::INSET));

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
