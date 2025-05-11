use crate::{
    strutil::TString,
    ui::{
        component::{text::TextStyle, Component, Event, EventCtx, Label, Never},
        constant::screen,
        display::{Color, Icon},
        geometry::{Alignment, Alignment2D, Direction, Insets, Offset, Point, Rect},
        shape::{self, Renderer, Text},
        util::Pager,
    },
};

use super::{super::fonts, theme};

/// Component rendered above ActionBar, showing one of these:
///     - a task instruction/hint with optional icon, e.g. "Confirm
///       transaction",
///     - a page counter e.g. "1 / 3", meaning the first screen of three total.
///
/// The instruction has adaptive height, depending on the text length. The
/// PageCounter is always of minimal component height (40px).
#[derive(Clone)]
pub struct Hint<'a> {
    area: Rect,
    content: HintContent<'a>,
    swipe_allow_up: bool,
    swipe_allow_down: bool,
    progress: i16,
    dir: Direction,
}

#[derive(Clone)]
#[allow(clippy::large_enum_variant)]
enum HintContent<'a> {
    Instruction(Instruction<'a>),
    PageCounter(PageCounter),
}

impl<'a> Hint<'a> {
    /// default height of the component [px]
    pub const HEIGHT_MINIMAL: i16 = 40;
    /// height of the multi line component [px]
    pub const HEIGHT_MAXIMAL: i16 = 66;
    /// margins from the edges of the screen [px]
    const HINT_INSETS: Insets = Insets::new(16, 24, 24, 24);

    fn from_content(content: HintContent<'a>) -> Self {
        Self {
            area: Rect::zero(),
            content,
            swipe_allow_down: false,
            swipe_allow_up: false,
            progress: 0,
            dir: Direction::Up,
        }
    }

    pub fn new_instruction<T: Into<TString<'static>>>(text: T, icon: Option<Icon>) -> Self {
        let instruction_component =
            Instruction::new(text.into(), theme::GREY, icon, Some(theme::GREY_LIGHT));
        Self::from_content(HintContent::Instruction(instruction_component))
    }

    pub fn new_instruction_green<T: Into<TString<'static>>>(text: T, icon: Option<Icon>) -> Self {
        let instruction_component = Instruction::new(
            text.into(),
            theme::GREEN_LIME,
            icon,
            Some(theme::GREEN_LIME),
        );
        Self::from_content(HintContent::Instruction(instruction_component))
    }

    pub fn new_warning<T: Into<TString<'static>>>(text: T) -> Self {
        let instruction_component = Instruction::new(
            text.into(),
            theme::GREY,
            Some(theme::ICON_INFO),
            Some(theme::ORANGE),
        );
        Self::from_content(HintContent::Instruction(instruction_component))
    }

    pub fn new_warning_severe<T: Into<TString<'static>>>(text: T) -> Self {
        let instruction_component = Instruction::new(
            text.into(),
            theme::RED,
            Some(theme::ICON_WARNING),
            Some(theme::RED),
        );
        Self::from_content(HintContent::Instruction(instruction_component))
    }

    pub fn new_page_counter() -> Self {
        Self::from_content(HintContent::PageCounter(PageCounter::new()))
    }

    pub fn with_swipe(self, swipe_direction: Direction) -> Self {
        match swipe_direction {
            Direction::Up => Self {
                swipe_allow_up: true,
                ..self
            },
            Direction::Down => Self {
                swipe_allow_down: true,
                ..self
            },
            _ => self,
        }
    }

    pub fn update(&mut self, pager: Pager) {
        if let HintContent::PageCounter(counter) = &mut self.content {
            counter.update(pager);
            self.swipe_allow_down = counter.pager.is_first();
            self.swipe_allow_up = counter.pager.is_last();
        }
    }

    /// Returns the height of the content including padding. In case of the
    /// instruction, the height is calculated based on the text length.
    pub fn height(&self) -> i16 {
        self.content.height() + Self::HINT_INSETS.top + Self::HINT_INSETS.bottom
    }
}

impl<'a> Component for Hint<'a> {
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        debug_assert!(bounds.width() == screen().width());
        debug_assert!(bounds.height() == self.height());
        let bounds = bounds.inset(Self::HINT_INSETS);

        if let HintContent::Instruction(instruction) = &mut self.content {
            let text_area = match instruction.icon {
                Some(_) => bounds.split_left(instruction.icon_width()).1,
                None => bounds,
            };
            instruction.label.place(text_area);
        }
        self.area = bounds;
        self.area
    }

    fn event(&mut self, _ctx: &mut EventCtx, _event: Event) -> Option<Self::Msg> {
        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.content.render(self.area, target);
    }
}

impl<'a> HintContent<'a> {
    fn height(&self) -> i16 {
        match self {
            HintContent::Instruction(instruction) => instruction
                .height()
                .clamp(Hint::HEIGHT_MINIMAL, Hint::HEIGHT_MAXIMAL),
            HintContent::PageCounter(_) => Hint::HEIGHT_MINIMAL,
        }
    }

    fn render<'s>(&'s self, area: Rect, target: &mut impl Renderer<'s>)
    where
        's: 'a,
    {
        match self {
            HintContent::Instruction(instruction) => instruction.render(target, area),
            HintContent::PageCounter(page_counter) => page_counter.render(target, area),
        }
    }
}

// Helper componet used within Hint for instruction/hint rendering.
#[derive(Clone)]
struct Instruction<'a> {
    label: Label<'a>,
    text_color: Color,
    icon: Option<Icon>,
    icon_color: Option<Color>,
}

impl<'a> Instruction<'a> {
    /// default style for instruction text
    const STYLE_INSTRUCTION: &'static TextStyle = &theme::firmware::TEXT_SMALL;
    /// margin between icon and text
    const ICON_OFFSET: Offset = Offset::x(24); // [px]

    fn new(
        text: TString<'a>,
        text_color: Color,
        icon: Option<Icon>,
        icon_color: Option<Color>,
    ) -> Self {
        let mut text_style = *Self::STYLE_INSTRUCTION;
        text_style.text_color = text_color;
        Self {
            label: Label::left_aligned(text, text_style).vertically_centered(),
            text_color,
            icon,
            icon_color,
        }
    }

    /// Calculates the width needed for the icon
    fn icon_width(&self) -> i16 {
        self.icon
            .map_or(0, |icon| icon.toif.width() + Self::ICON_OFFSET.x)
    }

    /// Calculates the height needed for the Instruction text to be rendered.
    fn height(&self) -> i16 {
        let text_area_width = screen().inset(Hint::HINT_INSETS).width() - self.icon_width();
        let calculated_height = self.label.text_height(text_area_width);
        debug_assert!(calculated_height <= Hint::HEIGHT_MAXIMAL);
        calculated_height
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>, area: Rect) {
        if let Some(icon) = self.icon {
            shape::ToifImage::new(area.left_center(), icon.toif)
                .with_align(Alignment2D::CENTER_LEFT)
                .with_fg(self.icon_color.unwrap_or(self.text_color))
                .render(target);
        };
        // the label got area without the icon in `place` function
        self.label.render(target);
    }
}

/// Helper component used within Hint for page count indication, rendered e.g.
/// as: '1 / 20'.
#[derive(Clone)]
struct PageCounter {
    pager: Pager,
}

impl PageCounter {
    fn new() -> Self {
        Self {
            pager: Pager::single_page(),
        }
    }

    fn update(&mut self, pager: Pager) {
        self.pager = pager
    }
}

impl PageCounter {
    fn render<'s>(&'s self, target: &mut impl Renderer<'s>, area: Rect) {
        let font = fonts::FONT_SATOSHI_REGULAR_22;
        let (color_num, color_icon) = if self.pager.is_last() {
            (theme::GREEN_LIGHT, theme::GREEN)
        } else {
            (theme::GREY, theme::GREY_DARK)
        };

        let string_curr = uformat!("{}", self.pager.current() + 1);
        let string_max = uformat!("{}", self.pager.total());

        // the counter is left aligned
        let offset_x = Offset::x(4); // spacing between foreslash and numbers
        let width_num_curr = font.text_width(&string_curr);
        let width_foreslash = theme::ICON_FORESLASH.toif.width();
        let width_num_max = font.text_width(&string_max);
        let width_total = width_num_curr + width_foreslash + width_num_max + 2 * offset_x.x;

        let counter_area = area.inset(Hint::HINT_INSETS);
        let counter_start_x = counter_area.bottom_left().x;
        let counter_y = font.vert_center(counter_area.y0, counter_area.y1, "0");
        let counter_end_x = counter_start_x + width_total;
        let base_num_curr = Point::new(counter_start_x, counter_y);
        let base_foreslash = Point::new(counter_start_x + width_num_curr + offset_x.x, counter_y);
        let base_num_max = Point::new(counter_end_x, counter_y);

        Text::new(base_num_curr, &string_curr, font)
            .with_align(Alignment::Start)
            .with_fg(color_num)
            .render(target);
        shape::ToifImage::new(base_foreslash, theme::ICON_FORESLASH.toif)
            .with_align(Alignment2D::BOTTOM_LEFT)
            .with_fg(color_icon)
            .render(target);
        Text::new(base_num_max, &string_max, font)
            .with_align(Alignment::End)
            .with_fg(color_num)
            .render(target);
    }
}

#[cfg(feature = "ui_debug")]
impl<'a> crate::trace::Trace for Hint<'a> {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("Hint");
        match &self.content {
            HintContent::Instruction(i) => {
                t.child("instruction", &i.label);
            }
            HintContent::PageCounter(counter) => {
                t.int("page curr", counter.pager.current().into());
                t.int("page max", counter.pager.total().into());
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_instruction_hint_height() {
        // FIXME: this test is fine but the `screen()` is not returning the right value
        // for eckhart println!("screen size: {:?}", screen().width());

        let with_padding = |h: i16| h + Hint::HINT_INSETS.top + Hint::HINT_INSETS.bottom;
        let hint_1line = Hint::new_instruction("Test", None);
        assert_eq!(hint_1line.content.height(), Hint::HEIGHT_MINIMAL);
        assert_eq!(hint_1line.height(), with_padding(Hint::HEIGHT_MINIMAL));

        let hint_2lines = Hint::new_instruction(
            "The word appears multiple times in the backup.",
            Some(theme::ICON_INFO),
        );
        assert_eq!(
            hint_2lines.content.height(),
            Instruction::STYLE_INSTRUCTION.text_font.text_height() * 2
        );
        assert_eq!(
            hint_2lines.height(),
            with_padding(Instruction::STYLE_INSTRUCTION.text_font.text_height() * 2)
        );

        let hint_3lines = Hint::new_instruction(
            "This is very long instruction which will span across at least three lines of the Hint component.",
            None,
        );
        assert_eq!(hint_3lines.content.height(), Hint::HEIGHT_MAXIMAL);
        assert_eq!(hint_3lines.height(), with_padding(Hint::HEIGHT_MAXIMAL));
    }
}
