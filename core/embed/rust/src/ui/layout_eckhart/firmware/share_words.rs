use crate::{
    strutil::TString,
    translations::TR,
    ui::{
        component::{
            swipe_detect::SwipeConfig, text::TextStyle, Component, Event, EventCtx, Label, Never,
            Paginate, Swipe,
        },
        flow::Swipable,
        geometry::{Alignment, Direction, Insets, Offset, Rect},
        shape::{Bar, Renderer, Text},
        util::Pager,
    },
};

use heapless::Vec;

use super::super::{
    component::Button,
    constant::SCREEN,
    firmware::{ActionBar, ActionBarMsg, Header, HeaderMsg, Hint},
    fonts, theme,
};

const MAX_WORDS: usize = 33; // super-shamir has 33 words, all other have less
type IndexVec = Vec<u8, MAX_WORDS>;

/// Full-screen component for rendering ShareWords.
pub struct ShareWordsScreen<'a> {
    header: Header,
    subtitle: Option<Label<'static>>,
    content: ShareWords<'a>,
    hint: Hint<'static>,
    action_bar: ActionBar,
    /// Common area for the content and hint
    area: Rect,
    page_swipe: Swipe,
    swipe_config: SwipeConfig,
}

pub enum ShareWordsScreenMsg {
    Cancelled,
    Confirmed,
}

impl<'a> ShareWordsScreen<'a> {
    const WORD_AREA_HEIGHT: i16 = 120;
    const SUBTITLE_HEIGHT: i16 = 44;
    const WORD_Y_OFFSET: i16 = 80 - Self::SUBTITLE_HEIGHT; // vertical distance from the subtitle
    const SUBTITLE_STYLE: TextStyle = theme::TEXT_MEDIUM_EXTRA_LIGHT;

    pub fn new(share_words_vec: Vec<TString<'static>, 33>, show_back_button: bool) -> Self {
        let content = ShareWords::new(share_words_vec);

        let right_button = Button::with_text(TR::buttons__continue.into());
        let mut action_bar = if show_back_button {
            ActionBar::new_double(Button::with_icon(theme::ICON_CHEVRON_UP), right_button)
        } else {
            ActionBar::new_single(right_button)
        };

        // Set action bar page counter
        action_bar.update(content.pager());

        let header = Header::new(TR::reset__recovery_wallet_backup_title.into());

        let mut hint = Hint::new_page_counter();
        hint.update(content.pager());

        Self {
            header,
            subtitle: None,
            content,
            hint,
            action_bar,
            area: Rect::zero(),
            page_swipe: Swipe::vertical(),
            swipe_config: SwipeConfig::new(),
        }
    }

    pub fn with_subtitle(mut self, subtitle: TString<'static>) -> Self {
        if !subtitle.is_empty() {
            self.subtitle = Some(Label::left_aligned(subtitle, Self::SUBTITLE_STYLE).top_aligned());
        }
        self
    }

    fn on_page_change(&mut self, direction: Direction) {
        // Update page based on the direction

        match direction {
            Direction::Up => {
                self.content.change_page(self.content.pager().next());
            }
            Direction::Down => {
                self.content.change_page(self.content.pager().prev());
            }
            _ => {}
        }

        // Update action bar content based on the current page
        self.action_bar.update(self.content.pager());

        // Update hint content based on the current page

        // Repeated words get a special hint
        if self.content.is_repeated() {
            self.hint = Hint::new_instruction_green(
                TR::reset__the_word_is_repeated,
                Some(theme::ICON_INFO),
            );
        // Other words get a page counter hint
        } else {
            self.hint = Hint::new_page_counter();
            self.hint.update(self.content.pager());
        }

        // use place function because the hint height is floating based on its content
        self.place(self.area);
    }
}

impl<'a> Swipable for ShareWordsScreen<'a> {
    fn get_pager(&self) -> Pager {
        self.content.pager()
    }
    fn get_swipe_config(&self) -> SwipeConfig {
        SwipeConfig::default()
    }
}

impl<'a> Component for ShareWordsScreen<'a> {
    type Msg = ShareWordsScreenMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        // assert full screen
        debug_assert_eq!(bounds.height(), SCREEN.height());
        debug_assert_eq!(bounds.width(), SCREEN.width());

        self.area = bounds;
        let (header_area, rest) = bounds.split_top(Header::HEADER_HEIGHT);
        let (subtitle_area, rest) = rest.split_top(Self::SUBTITLE_HEIGHT);
        let (rest, action_bar_area) = rest.split_bottom(ActionBar::ACTION_BAR_HEIGHT);
        let (mut content_area, hint_area) = rest.split_bottom(self.hint.height());

        // Use constant y offset for the word area because the height is floating
        content_area = content_area
            .inset(Insets::top(Self::WORD_Y_OFFSET))
            .inset(theme::SIDE_INSETS)
            .with_height(Self::WORD_AREA_HEIGHT);

        self.page_swipe.place(bounds);
        self.header.place(header_area);
        self.subtitle.place(subtitle_area.inset(theme::SIDE_INSETS));
        self.content.place(content_area);
        self.hint.place(hint_area);
        self.action_bar.place(action_bar_area);

        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if let Some(swipe) = self.page_swipe.event(ctx, event) {
            // We have detected a vertical swipe. Change the keyboard page.
            self.on_page_change(swipe);
            ctx.request_paint();
            return None;
        }

        if let Some(HeaderMsg::Cancelled) = self.header.event(ctx, event) {
            return Some(ShareWordsScreenMsg::Cancelled);
        }

        if let Some(msg) = self.action_bar.event(ctx, event) {
            match msg {
                ActionBarMsg::Cancelled => {
                    return Some(ShareWordsScreenMsg::Cancelled);
                }
                ActionBarMsg::Confirmed => {
                    return Some(ShareWordsScreenMsg::Confirmed);
                }
                ActionBarMsg::Prev => {
                    self.on_page_change(Direction::Down);
                    return None;
                }
                ActionBarMsg::Next => {
                    self.on_page_change(Direction::Up);
                    return None;
                }
            }
        }

        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.header.render(target);
        self.subtitle.render(target);
        self.content.render(target);
        self.hint.render(target);
        self.action_bar.render(target);
    }
}

#[cfg(feature = "ui_debug")]
impl<'a> crate::trace::Trace for ShareWordsScreen<'a> {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("TextScreen");
        t.child("Header", &self.header);
        t.child("Content", &self.content);
        t.child("Hint", &self.hint);
        t.child("ActionBar", &self.action_bar);
    }
}

/// Component showing mnemonic/share words during backup procedure. Model T3W1
/// contains one word per screen. A user is instructed to swipe up/down to see
/// next/previous word.
struct ShareWords<'a> {
    share_words: Vec<TString<'a>, MAX_WORDS>,
    area: Rect,
    repeated_indices: IndexVec,
    pager: Pager,
}

impl<'a> ShareWords<'a> {
    const AREA_WORD_HEIGHT: i16 = 120;
    const ORDINAL_PADDING: i16 = 16;

    pub fn new(share_words: Vec<TString<'a>, MAX_WORDS>) -> Self {
        let repeated_indices = Self::find_repeated(share_words.as_slice());
        let pager = Pager::new(share_words.len() as u16);
        Self {
            share_words,
            area: Rect::zero(),
            repeated_indices,
            pager,
        }
    }

    pub fn is_repeated(&self) -> bool {
        self.repeated_indices
            .contains(&(self.pager().current() as u8))
    }

    fn find_repeated(share_words: &[TString]) -> IndexVec {
        let mut repeated_indices = IndexVec::new();
        for i in (0..share_words.len()).rev() {
            let word = share_words[i];
            if share_words[..i].contains(&word) {
                unwrap!(repeated_indices.push(i as u8));
            }
        }
        repeated_indices.reverse();
        repeated_indices
    }
}

// Pagination
impl<'a> Paginate for ShareWords<'a> {
    fn pager(&self) -> Pager {
        self.pager
    }

    fn change_page(&mut self, to_page: u16) {
        let to_page = to_page.min(self.pager.total() - 1);

        // Update the pager
        self.pager.set_current(to_page);
    }
}

impl<'a> Component for ShareWords<'a> {
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.area = bounds;
        bounds
    }

    fn event(&mut self, _ctx: &mut EventCtx, _event: Event) -> Option<Self::Msg> {
        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        // the ordinal number of the current word
        let ordinal_val = self.pager().current() as u8 + 1;
        let ordinal_pos = self.area.top_left();
        let ordinal = uformat!("{}", ordinal_val);
        Text::new(ordinal_pos, &ordinal, fonts::FONT_SATOSHI_REGULAR_38)
            .with_fg(theme::GREY)
            .render(target);

        // Render lines as bars with the with 1px
        let top_line = Rect::from_bottom_right_and_size(
            self.area.top_right(),
            Offset::new(
                self.area.width()
                    - theme::TEXT_REGULAR.text_font.text_width(&ordinal)
                    - Self::ORDINAL_PADDING,
                1,
            ),
        );
        let bottom_line = Rect::from_bottom_right_and_size(
            self.area.bottom_right(),
            Offset::new(self.area.width(), 1),
        );

        Bar::new(top_line)
            .with_fg(theme::GREY_EXTRA_DARK)
            .render(target);

        Bar::new(bottom_line)
            .with_fg(theme::GREY_EXTRA_DARK)
            .render(target);

        let word = self.share_words[self.pager().current() as usize];
        let font = fonts::FONT_SATOSHI_EXTRALIGHT_72;

        let word_baseline = self.area.center() + Offset::y(font.visible_text_height("A") / 2);
        word.map(|w| {
            Text::new(word_baseline, w, font)
                .with_align(Alignment::Center)
                .render(target);
        });
    }
}

#[cfg(feature = "ui_debug")]
impl<'a> crate::trace::Trace for ShareWords<'a> {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("ShareWordsInner");
        let word = &self.share_words[self.pager().current() as usize];
        let content = word.map(|w| uformat!("{}. {}\n", self.pager().current() + 1, w));
        t.string("screen_content", content.as_str().into());
        t.int("page_count", self.share_words.len() as i64)
    }
}

#[cfg(test)]
mod tests {
    use super::{super::super::constant::SCREEN, *};

    #[test]
    fn test_component_heights_fit_screen() {
        assert!(
            Header::HEADER_HEIGHT
                + ShareWordsScreen::SUBTITLE_HEIGHT
                + ShareWordsScreen::WORD_Y_OFFSET
                + ShareWords::AREA_WORD_HEIGHT
                + Hint::HEIGHT_MAXIMAL
                <= SCREEN.height(),
            "Components overflow the screen height",
        );
    }
}
