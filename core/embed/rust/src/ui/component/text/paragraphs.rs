use heapless::Vec;

use crate::{
    strutil::TString,
    ui::{
        component::{paginated::SinglePage, Component, Event, EventCtx, Never, PaginateFull},
        display::{font::Font, toif::Icon, Color},
        geometry::{Alignment, Dimensions, Insets, LinearPlacement, Offset, Point, Rect},
        shape::{self, Renderer},
        util::Pager,
    },
};

use super::layout::{LayoutFit, TextLayout, TextStyle};

/// Used as an upper bound of number of different styles we may render on single
/// page.
pub const MAX_LINES: usize = 10;
/// Maximum space between paragraphs. Actual result may be smaller (even 0) if
/// it would make paragraphs overflow the bounding box.
pub const DEFAULT_SPACING: i16 = 0;
/// Offset of paragraph text from the top of the paragraph bounding box. Tweak
/// these values to get nice alignment of baselines relative to the surrounding
/// components.
pub const PARAGRAPH_TOP_SPACE: i16 = -1;
/// Offset of paragraph bounding box bottom relative to bottom of its text.
pub const PARAGRAPH_BOTTOM_SPACE: i16 = 5;

pub type ParagraphVecLong<'a> = Vec<Paragraph<'a>, 32>;
pub type ParagraphVecShort<'a> = Vec<Paragraph<'a>, 8>;

pub trait ParagraphSource<'a> {
    /// Return text and associated style for given paragraph index and character
    /// offset within the paragraph.
    fn at(&self, index: usize, offset: usize) -> Paragraph<'a>;

    /// Number of paragraphs.
    fn size(&self) -> usize;

    fn into_paragraphs(self) -> Paragraphs<Self>
    where
        Self: Sized,
    {
        Paragraphs::new(self)
    }
}

#[derive(Clone)]
pub struct Paragraphs<T> {
    area: Rect,
    placement: LinearPlacement,
    offset: PageOffset,
    visible: Vec<TextLayoutProxy, MAX_LINES>,
    source: T,
    pager: Pager,
}

impl<'a, T> Paragraphs<T>
where
    T: ParagraphSource<'a>,
{
    pub fn new(source: T) -> Self {
        Self {
            area: Rect::zero(),
            placement: LinearPlacement::vertical()
                .align_at_center()
                .with_spacing(DEFAULT_SPACING),
            offset: PageOffset::default(),
            visible: Vec::new(),
            source,
            pager: Pager::single_page(),
        }
    }

    pub fn with_placement(mut self, placement: LinearPlacement) -> Self {
        self.placement = placement;
        self
    }

    pub fn with_spacing(mut self, spacing: i16) -> Self {
        self.placement = self.placement.with_spacing(spacing);
        self
    }

    pub fn inner(&self) -> &T {
        &self.source
    }

    pub fn mutate<R>(&mut self, func: impl Fn(&mut T) -> R) -> R {
        let result = func(&mut self.source);
        self.recalculate_pages();
        result
    }

    pub fn area(&self) -> Rect {
        let mut result: Option<Rect> = None;
        Self::foreach_visible(
            &self.source,
            &self.visible,
            self.offset,
            &mut |layout, _content| {
                result = result.map_or(Some(layout.bounds), |r| Some(r.union(layout.bounds)));
            },
        );
        result.unwrap_or(self.area)
    }

    /// Update bounding boxes of paragraphs on the current page. First determine
    /// the number of visible paragraphs and their sizes. These are then
    /// arranged according to the layout.
    fn change_offset(&mut self, offset: PageOffset) {
        self.offset = offset;
        Self::dyn_change_offset(self.area, offset, &self.source, self.visible.as_mut());
        self.placement.arrange(self.area, &mut self.visible);
    }

    /// Helper for `change_offset` which should not get monomorphized as it
    /// doesn't refer to T or Self.
    fn dyn_change_offset(
        mut area: Rect,
        mut offset: PageOffset,
        source: &dyn ParagraphSource<'_>,
        visible: &mut Vec<TextLayoutProxy, MAX_LINES>,
    ) {
        visible.clear();
        let full_height = area.height();

        while offset.par < source.size() {
            let advance = offset.advance(area, source, full_height);
            if let Some(layout) = advance.layout {
                unwrap!(visible.push(layout));
            }
            if let Some(remaining_area) = advance.remaining_area {
                #[cfg(feature = "ui_debug")]
                assert_eq!(advance.offset.par, offset.par + 1);
                area = remaining_area;
                offset = advance.offset;
            } else {
                break;
            }
        }
    }

    fn break_pages_from(&self, offset: Option<PageOffset>) -> PageBreakIterator<T> {
        PageBreakIterator {
            paragraphs: self,
            current: offset,
        }
    }

    /// Break pages from the start of the document.
    ///
    /// The first pagebreak is at the start of the first screen.
    fn break_pages_from_start(&self) -> PageBreakIterator<T> {
        self.break_pages_from(None)
    }

    /// Break pages, continuing from the current page.
    ///
    /// The first pagebreak is at the start of the next screen.
    fn break_pages_from_next(&self) -> PageBreakIterator<T> {
        self.break_pages_from(Some(self.offset))
    }

    /// Iterate over visible layouts (bounding box, style) together
    /// with corresponding string content. Should not get monomorphized.
    fn foreach_visible<'b>(
        source: &'b dyn ParagraphSource<'a>,
        visible: &'b [TextLayoutProxy],
        offset: PageOffset,
        func: &mut dyn FnMut(&TextLayout, &str),
    ) {
        let mut vis_iter = visible.iter();
        let mut chr = offset.chr;

        for par in offset.par..source.size() {
            let s = source.at(par, chr).content;
            if s.is_empty() {
                chr = 0;
                continue;
            }
            if let Some(layout_proxy) = vis_iter.next() {
                let layout = layout_proxy.layout(source);
                s.map(|t| func(&layout, t));
            } else {
                break;
            }
            chr = 0;
        }
    }

    fn recalculate_pages(&mut self) {
        if self.area.is_empty() {
            return;
        }
        let total_pages = self.break_pages_from_start().count().max(1);
        self.pager = Pager::new(total_pages as u16);
        self.offset = PageOffset::default();
        self.change_offset(self.offset);
    }
}

impl<'a> Paragraphs<Paragraph<'a>> {
    pub fn content(&self) -> &TString<'a> {
        self.source.content()
    }

    pub fn update<T: Into<TString<'a>>>(&mut self, content: T) {
        self.source.update(content);
        self.recalculate_pages();
    }
}

impl<'a, T> Component for Paragraphs<T>
where
    T: ParagraphSource<'a>,
{
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        let recalc = self.area != bounds;
        self.area = bounds;
        if recalc {
            self.recalculate_pages();
        }
        self.area
    }

    fn event(&mut self, _ctx: &mut EventCtx, _event: Event) -> Option<Self::Msg> {
        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        Self::foreach_visible(
            &self.source,
            &self.visible,
            self.offset,
            &mut |layout, content| {
                layout.render_text(content, target);
            },
        )
    }
}

impl<'a, T> PaginateFull for Paragraphs<T>
where
    T: ParagraphSource<'a>,
{
    fn pager(&self) -> Pager {
        self.pager
    }

    fn change_page(&mut self, to_page: u16) {
        use core::cmp::Ordering;

        let offset = match to_page.cmp(&self.pager.current()) {
            Ordering::Equal => return,
            Ordering::Greater => self
                .break_pages_from_next()
                .nth((to_page - self.pager.current() - 1) as usize),
            Ordering::Less => self.break_pages_from_start().nth(to_page as usize),
        };
        if let Some(offset) = offset {
            self.change_offset(offset);
            self.pager.set_current(to_page);
        } else {
            // Should not happen, set index to first paragraph and render empty page.
            self.offset = PageOffset::default();
            self.visible.clear();
            self.pager.set_current(0);
        }
    }
}

#[cfg(feature = "ui_debug")]
pub mod trace {
    use crate::ui::component::text::layout::trace::TraceSink;

    use super::*;

    impl<'a, T: ParagraphSource<'a>> crate::trace::Trace for Paragraphs<T> {
        fn trace(&self, t: &mut dyn crate::trace::Tracer) {
            t.string("component", "Paragraphs".into());
            t.in_list("paragraphs", &|par_list| {
                Self::foreach_visible(
                    &self.source,
                    &self.visible,
                    self.offset,
                    &mut |layout, content| {
                        par_list.in_list(&|par| {
                            layout.layout_text(
                                content,
                                &mut layout.initial_cursor(),
                                &mut TraceSink(par),
                            );
                        });
                    },
                );
            });
        }
    }
}

#[derive(Clone, Copy)]
pub struct Paragraph<'a> {
    /// Paragraph text.
    content: TString<'a>,
    /// Paragraph style.
    style: &'static TextStyle,
    /// Paragraph alignment.
    align: Alignment,
    /// Place next paragraph on new page.
    break_after: bool,
    /// Try to keep this and the next paragraph on the same page. NOTE: doesn't
    /// work if two or more subsequent paragraphs have this flag.
    no_break: bool,
    padding_top: i16,
    padding_bottom: i16,
}

impl<'a> Paragraph<'a> {
    pub fn new<T: Into<TString<'a>>>(style: &'static TextStyle, content: T) -> Self {
        Self {
            content: content.into(),
            style,
            align: Alignment::Start,
            break_after: false,
            no_break: false,
            padding_top: PARAGRAPH_TOP_SPACE,
            padding_bottom: PARAGRAPH_BOTTOM_SPACE,
        }
    }

    pub const fn centered(mut self) -> Self {
        self.align = Alignment::Center;
        self
    }

    pub const fn break_after(mut self) -> Self {
        self.break_after = true;
        self
    }

    pub const fn no_break(mut self) -> Self {
        self.no_break = true;
        self
    }

    pub const fn with_top_padding(mut self, padding: i16) -> Self {
        self.padding_top = padding;
        self
    }

    pub const fn with_bottom_padding(mut self, padding: i16) -> Self {
        self.padding_bottom = padding;
        self
    }

    pub fn content(&self) -> &TString<'a> {
        &self.content
    }

    pub fn update<T: Into<TString<'a>>>(&mut self, content: T) {
        self.content = content.into()
    }

    pub fn skip_prefix(&self, offset: usize) -> Paragraph<'a> {
        let content = self.content.skip_prefix(offset);
        Paragraph { content, ..*self }
    }

    fn layout(&self, area: Rect) -> TextLayout {
        TextLayout {
            padding_top: self.padding_top,
            padding_bottom: self.padding_bottom,
            ..TextLayout::new(*self.style)
                .with_align(self.align)
                .with_bounds(area)
        }
    }
}

#[derive(Clone)]
struct TextLayoutProxy {
    offset: PageOffset,
    bounds: Rect,
}

impl TextLayoutProxy {
    fn new(offset: PageOffset, bounds: Rect) -> Self {
        Self { offset, bounds }
    }

    fn layout(&self, source: &dyn ParagraphSource<'_>) -> TextLayout {
        let content = source.at(self.offset.par, self.offset.chr);
        let mut layout = content.layout(self.bounds);
        layout.continues_from_prev_page = self.offset.chr > 0;

        layout
    }
}

impl Dimensions for TextLayoutProxy {
    fn fit(&mut self, area: Rect) {
        self.bounds = area;
    }

    fn area(&self) -> Rect {
        self.bounds
    }
}

#[derive(Clone, Copy, Debug, Default, PartialEq, Eq, PartialOrd, Ord)]
struct PageOffset {
    /// Index of paragraph.
    par: usize,

    /// Index of (the first byte of) the character in the paragraph.
    chr: usize,
}

/// Helper struct for `PageOffset::advance`
struct PageOffsetAdvance {
    offset: PageOffset,
    remaining_area: Option<Rect>,
    layout: Option<TextLayoutProxy>,
}

impl PageOffset {
    /// Given a `PageOffset` and a `Rect` area, returns:
    ///
    /// - The next offset.
    /// - Part of `area` that remains free after the current offset is rendered
    ///   into it, or `None` if we've reached the end of the page.
    /// - The `TextLayout` for the current offset, or `None` if `area` is too
    ///   small to render any text.
    ///
    /// If the returned remaining area is not None then it holds that
    /// `next_offset.par == self.par + 1`.
    fn advance(
        mut self,
        area: Rect,
        source: &dyn ParagraphSource<'_>,
        full_height: i16,
    ) -> PageOffsetAdvance {
        let paragraph = source.at(self.par, self.chr);

        // Skip empty paragraphs.
        if paragraph.content().is_empty() {
            self.par += 1;
            self.chr = 0;
            return PageOffsetAdvance {
                offset: self,
                remaining_area: Some(area),
                layout: None,
            };
        }

        // Handle the `no_break` flag used to keep key-value pair on the same page:
        // * no_break is set
        // * we're at the start of a paragraph ("key")
        // * there is a next paragraph ("value")
        // then check if the pair fits on the next page.
        if paragraph.no_break && self.chr == 0 && self.par + 1 < source.size() {
            let next_paragraph = source.at(self.par + 1, 0);
            if Self::should_place_pair_on_next_page(&paragraph, &next_paragraph, area, full_height)
            {
                return PageOffsetAdvance {
                    offset: self,
                    remaining_area: None,
                    layout: None,
                };
            }
        }

        // Find out the dimensions of the paragraph at given char offset.
        let mut layout = paragraph.layout(area);
        layout.continues_from_prev_page = self.chr > 0;
        let fit = paragraph.content().map(|t| layout.fit_text(t));
        let (used, remaining_area) = area.split_top(fit.height());

        let layout = TextLayoutProxy::new(self, used);

        let page_full: bool;
        match fit {
            LayoutFit::Fitting { .. } => {
                // Continue with start of next paragraph.
                self.par += 1;
                self.chr = 0;
                // Handle hard break if requested for this paragraph.
                page_full = paragraph.break_after;
            }
            LayoutFit::OutOfBounds {
                processed_chars, ..
            } => {
                // Reached end of the page and not all content fits.
                self.chr += processed_chars;
                // Do not render more paragraphs.
                page_full = true;
            }
        }

        PageOffsetAdvance {
            offset: self,
            remaining_area: (!page_full).then_some(remaining_area),
            layout: (fit.height() > 0).then_some(layout),
        }
    }

    fn should_place_pair_on_next_page(
        this_paragraph: &Paragraph<'_>,
        next_paragraph: &Paragraph<'_>,
        area: Rect,
        full_height: i16,
    ) -> bool {
        // Never break if we're at the beginning of the page.
        let remaining_height = area.height();
        if remaining_height >= full_height {
            return false;
        }

        let full_area = area.with_height(full_height);
        let key_height = this_paragraph
            .content()
            .map(|t| this_paragraph.layout(full_area).fit_text(t).height());
        let val_height = next_paragraph
            .content()
            .map(|t| next_paragraph.layout(full_area).fit_text(t).height());
        let screen_full_threshold = this_paragraph.style.text_font.line_height()
            + next_paragraph.style.text_font.line_height();

        if key_height + val_height > remaining_height {
            return
                // There are only ~2 remaining lines, don't try to fit and put everything on the
                // next page.
                (remaining_height <= screen_full_threshold)
                // More than 2 remaining lines so try to fit something -- but won't
                // fit at least one line of value.
                || (val_height > 0 && key_height > remaining_height)
                // Whole property won't fit to the page, but it will fit on a page
                // by itself.
                || (key_height + val_height <= full_height);
        }

        // None of the above, continue fitting on the same page.
        false
    }
}

struct PageBreakIterator<'a, T> {
    /// Reference to paragraph vector.
    paragraphs: &'a Paragraphs<T>,

    /// Current offset, or `None` before first `next()` call.
    current: Option<PageOffset>,
}

impl<'a, T: ParagraphSource<'a>> PageBreakIterator<'_, T> {
    fn dyn_next(
        mut area: Rect,
        paragraphs: &dyn ParagraphSource<'_>,
        mut offset: PageOffset,
    ) -> Option<PageOffset> {
        let full_height = area.height();

        while offset.par < paragraphs.size() {
            let advance = offset.advance(area, paragraphs, full_height);
            if advance.offset.par >= paragraphs.size() {
                // Last page.
                return None;
            } else if let Some(remaining_area) = advance.remaining_area {
                #[cfg(feature = "ui_debug")]
                assert_eq!(advance.offset.par, offset.par + 1);
                area = remaining_area;
                offset = advance.offset;
            } else {
                return Some(advance.offset);
            }
        }

        None
    }
}

/// Yields indices to beginnings of successive pages. First value is always
/// `PageOffset { 0, 0 }` even if the paragraph vector is empty.
impl<'a, T: ParagraphSource<'a>> Iterator for PageBreakIterator<'_, T> {
    /// `PageOffset` denotes the first paragraph that is rendered and a
    /// character offset in that paragraph.
    type Item = PageOffset;

    fn next(&mut self) -> Option<Self::Item> {
        let first = self.current.is_none();
        let current = self.current.get_or_insert_with(PageOffset::default);
        if first {
            return self.current;
        }

        let next = Self::dyn_next(self.paragraphs.area, &self.paragraphs.source, *current);
        if next.is_some() {
            // Better panic than infinite loop.
            assert_ne!(next, self.current);
            self.current = next;
        }
        next
    }
}

pub struct Checklist<T> {
    area: Rect,
    paragraphs: Paragraphs<T>,
    current: usize,
    icon_current: Icon,
    icon_done: Icon,
    icon_done_color: Option<Color>,
    numeral_font: Option<Font>,
    /// How wide will the left icon column be
    check_width: i16,
    /// Offset of the icon representing DONE
    done_offset: Offset,
    /// Offset of the icon representing CURRENT
    current_offset: Offset,
    /// Offset of the numeral representing the ordinal number of the task
    numeral_offset: Offset,
}

impl<'a, T> Checklist<T>
where
    T: ParagraphSource<'a>,
{
    pub fn from_paragraphs(
        icon_current: Icon,
        icon_done: Icon,
        current: usize,
        paragraphs: Paragraphs<T>,
    ) -> Self {
        Self {
            area: Rect::zero(),
            paragraphs,
            current,
            icon_current,
            icon_done,
            icon_done_color: None,
            numeral_font: None,
            check_width: 0,
            done_offset: Offset::zero(),
            current_offset: Offset::zero(),
            numeral_offset: Offset::zero(),
        }
    }

    pub fn with_check_width(mut self, check_width: i16) -> Self {
        self.check_width = check_width;
        self
    }

    pub fn with_done_offset(mut self, done_offset: Offset) -> Self {
        self.done_offset = done_offset;
        self
    }

    pub fn with_current_offset(mut self, current_offset: Offset) -> Self {
        self.current_offset = current_offset;
        self
    }

    pub fn with_icon_done_color(mut self, col: Color) -> Self {
        self.icon_done_color = Some(col);
        self
    }

    pub fn with_numerals(mut self, numerals_font: Font) -> Self {
        self.numeral_font = Some(numerals_font);
        self
    }

    pub fn with_numeral_offset(mut self, offset: Offset) -> Self {
        self.numeral_offset = offset;
        self
    }

    fn render_left_column<'s>(&self, target: &mut impl Renderer<'s>) {
        let current_visible = self.current.saturating_sub(self.paragraphs.offset.par);
        for (i, layout) in self.paragraphs.visible.iter().enumerate() {
            let l = &layout.layout(&self.paragraphs.source);
            let base = Point::new(self.area.x0, l.bounds.y0);
            if i < current_visible {
                // finished tasks - labeled with icon "done"
                let color = self.icon_done_color.unwrap_or(l.style.text_color);
                self.render_icon(base + self.done_offset, self.icon_done, color, target)
            } else {
                // current and future tasks - ordinal numbers or icon on current task
                if let Some(font) = self.numeral_font {
                    let offset = self.numeral_offset;
                    self.render_numeral(base + offset, i, font, l.style.text_color, target);
                } else if i == current_visible {
                    let color = l.style.text_color;
                    self.render_icon(base + self.current_offset, self.icon_current, color, target);
                }
            }
        }
    }

    fn render_numeral<'s>(
        &self,
        base_point: Point,
        n: usize,
        font: Font,
        color: Color,
        target: &mut impl Renderer<'s>,
    ) {
        let numeral = uformat!("{}.", n + 1);
        shape::Text::new(base_point, numeral.as_str(), font)
            .with_fg(color)
            .render(target);
    }

    fn render_icon<'s>(
        &self,
        base_point: Point,
        icon: Icon,
        color: Color,
        target: &mut impl Renderer<'s>,
    ) {
        shape::ToifImage::new(base_point, icon.toif)
            .with_fg(color)
            .render(target);
    }
}

impl<'a, T> Component for Checklist<T>
where
    T: ParagraphSource<'a>,
{
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.area = bounds;
        let para_area = bounds.inset(Insets::left(self.check_width));
        self.paragraphs.place(para_area);
        self.area
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        self.paragraphs.event(ctx, event)
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.paragraphs.render(target);
        self.render_left_column(target);
    }
}

impl<T> SinglePage for Checklist<T> {}

#[cfg(feature = "ui_debug")]
impl<'a, T: ParagraphSource<'a>> crate::trace::Trace for Checklist<T> {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("Checklist");
        t.int("current", self.current as i64);
        t.child("items", &self.paragraphs);
    }
}

#[cfg(feature = "micropython")]
mod micropython {
    use crate::{error::Error, micropython::obj::Obj, ui::layout::obj::ComponentMsgObj};
    impl<'a, T: super::ParagraphSource<'a>> ComponentMsgObj for super::Checklist<T> {
        fn msg_try_into_obj(&self, _msg: Self::Msg) -> Result<Obj, Error> {
            unreachable!();
        }
    }
}

pub trait VecExt<'a> {
    fn add(&mut self, paragraph: Paragraph<'a>) -> &mut Self;
}

impl<'a, const N: usize> VecExt<'a> for Vec<Paragraph<'a>, N> {
    fn add(&mut self, paragraph: Paragraph<'a>) -> &mut Self {
        if paragraph.content().is_empty() {
            return self;
        }
        if self.push(paragraph).is_err() {
            #[cfg(feature = "ui_debug")]
            fatal_error!("Paragraph list is full");
        }
        self
    }
}

impl<'a, const N: usize> ParagraphSource<'a> for Vec<Paragraph<'a>, N> {
    fn at(&self, index: usize, offset: usize) -> Paragraph<'a> {
        let para = &self[index];
        para.skip_prefix(offset)
    }

    fn size(&self) -> usize {
        self.len()
    }
}

impl<'a, const N: usize> ParagraphSource<'a> for [Paragraph<'a>; N] {
    fn at(&self, index: usize, offset: usize) -> Paragraph<'a> {
        let para = &self[index];
        para.skip_prefix(offset)
    }

    fn size(&self) -> usize {
        self.len()
    }
}

impl<'a> ParagraphSource<'a> for Paragraph<'a> {
    fn at(&self, index: usize, offset: usize) -> Paragraph<'a> {
        assert_eq!(index, 0);
        self.skip_prefix(offset)
    }

    fn size(&self) -> usize {
        1
    }
}
