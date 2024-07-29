use heapless::Vec;

use crate::{
    strutil::TString,
    ui::{
        component::{Component, Event, EventCtx, Never, Paginate},
        display::{toif::Icon, Color, Font},
        geometry::{
            Alignment, Alignment2D, Dimensions, Insets, LinearPlacement, Offset, Point, Rect,
        },
        shape,
        shape::Renderer,
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

    pub fn inner_mut(&mut self) -> &mut T {
        &mut self.source
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
            let (next_offset, remaining_area, layout) = offset.advance(area, source, full_height);
            if let Some(layout) = layout {
                unwrap!(visible.push(layout));
            }
            if let Some(remaining_area) = remaining_area {
                #[cfg(feature = "ui_debug")]
                assert_eq!(next_offset.par, offset.par + 1);
                area = remaining_area;
                offset = next_offset;
            } else {
                break;
            }
        }
    }

    fn break_pages(&self) -> PageBreakIterator<T> {
        PageBreakIterator {
            paragraphs: self,
            current: None,
        }
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
}

impl<'a, T> Component for Paragraphs<T>
where
    T: ParagraphSource<'a>,
{
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.area = bounds;
        self.change_offset(self.offset);
        self.area
    }

    fn event(&mut self, _ctx: &mut EventCtx, _event: Event) -> Option<Self::Msg> {
        None
    }

    fn paint(&mut self) {
        Self::foreach_visible(
            &self.source,
            &self.visible,
            self.offset,
            &mut |layout, content| {
                layout.render_text(content);
            },
        )
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        Self::foreach_visible(
            &self.source,
            &self.visible,
            self.offset,
            &mut |layout, content| {
                layout.render_text2(content, target);
            },
        )
    }
}

impl<'a, T> Paginate for Paragraphs<T>
where
    T: ParagraphSource<'a>,
{
    fn page_count(&mut self) -> usize {
        // There's always at least one page.
        self.break_pages().count().max(1)
    }

    fn change_page(&mut self, to_page: usize) {
        if let Some(offset) = self.break_pages().nth(to_page) {
            self.change_offset(offset)
        } else {
            // Should not happen, set index to first paragraph and render empty page.
            self.offset = PageOffset::default();
            self.visible.clear()
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

#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
struct PageOffset {
    /// Index of paragraph.
    par: usize,

    /// Index of (the first byte of) the character in the paragraph.
    chr: usize,
}

impl PageOffset {
    /// Given an `PageOffset` and a `Rect` area, returns:
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
    ) -> (PageOffset, Option<Rect>, Option<TextLayoutProxy>) {
        let paragraph = source.at(self.par, self.chr);

        // Skip empty paragraphs.
        if paragraph.content().is_empty() {
            self.par += 1;
            self.chr = 0;
            return (self, Some(area), None);
        }

        // Handle the `no_break` flag used to keep key-value pair on the same page.
        if paragraph.no_break && self.chr == 0 {
            if let Some(next_paragraph) =
                (self.par + 1 < source.size()).then(|| source.at(self.par + 1, 0))
            {
                if Self::should_place_pair_on_next_page(
                    &paragraph,
                    &next_paragraph,
                    area,
                    full_height,
                ) {
                    return (self, None, None);
                }
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

        (
            self,
            Some(remaining_area).filter(|_| !page_full),
            Some(layout).filter(|_| fit.height() > 0),
        )
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
            let (next_offset, remaining_area, _layout) =
                offset.advance(area, paragraphs, full_height);
            if next_offset.par >= paragraphs.size() {
                // Last page.
                return None;
            } else if let Some(remaining_area) = remaining_area {
                #[cfg(feature = "ui_debug")]
                assert_eq!(next_offset.par, offset.par + 1);
                area = remaining_area;
                offset = next_offset;
            } else {
                return Some(next_offset);
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
    show_numerals: bool,
    /// How wide will the left icon column be
    check_width: i16,
    /// Offset of the icon representing DONE
    done_offset: Offset,
    /// Offset of the icon representing CURRENT
    current_offset: Offset,
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
            show_numerals: false,
            check_width: 0,
            done_offset: Offset::zero(),
            current_offset: Offset::zero(),
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

    pub fn with_numerals(mut self) -> Self {
        self.show_numerals = true;
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
                if self.show_numerals {
                    let num_offset = Offset::new(4, Font::NORMAL.visible_text_height("1"));
                    self.render_numeral(base + num_offset, i, l.style.text_color, target);
                } else if i == current_visible {
                    let color = l.style.text_color;
                    self.render_icon(base + self.current_offset, self.icon_current, color, target);
                }
            }
        }
    }

    fn paint_icon(&self, layout: &TextLayout, icon: Icon, offset: Offset) {
        let top_left = Point::new(self.area.x0, layout.bounds.y0);
        icon.draw(
            top_left + offset,
            Alignment2D::TOP_LEFT,
            layout.style.text_color,
            layout.style.background_color,
        );
    }

    fn render_numeral<'s>(
        &self,
        base_point: Point,
        n: usize,
        color: Color,
        target: &mut impl Renderer<'s>,
    ) {
        let numeral = uformat!("{}.", n + 1);
        shape::Text::new(base_point, numeral.as_str())
            .with_font(Font::SUB)
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

    fn paint(&mut self) {
        self.paragraphs.paint();

        let current_visible = self.current.saturating_sub(self.paragraphs.offset.par);
        for layout in self.paragraphs.visible.iter().take(current_visible) {
            self.paint_icon(
                &layout.layout(&self.paragraphs.source),
                self.icon_done,
                self.done_offset,
            );
        }
        if let Some(layout) = self.paragraphs.visible.iter().nth(current_visible) {
            self.paint_icon(
                &layout.layout(&self.paragraphs.source),
                self.icon_current,
                self.current_offset,
            );
        }
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.paragraphs.render(target);
        self.render_left_column(target);
    }
}

impl<'a, T> Paginate for Checklist<T>
where
    T: ParagraphSource<'a>,
{
    fn page_count(&mut self) -> usize {
        1
    }

    fn change_page(&mut self, _to_page: usize) {}
}

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
