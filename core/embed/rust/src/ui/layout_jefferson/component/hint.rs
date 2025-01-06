use crate::{
    strutil::TString,
    ui::{
        component::{text::TextStyle, Component, Event, EventCtx, Never},
        display::{Color, Font, Icon},
        event::SwipeEvent,
        geometry::{Alignment, Alignment2D, Direction, Offset, Point, Rect},
        lerp::Lerp,
        shape::{self, Renderer, Text},
    },
};

use super::theme;

/// Component rendered above ActionBar, showing one of these:
///     - a task instruction/hint with optional icon, e.g. "Confirm
///       transaction",
///     - a page counter e.g. "1 / 3", meaning the first screen of three total.
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
enum HintContent<'a> {
    Instruction(Instruction<'a>),
    PageCounter(PageCounter),
}

impl<'a> Hint<'a> {
    /// height of the single line component [px]
    pub const SINGLE_LINE_HEIGHT: i16 = 40;
    /// height of the multi line component [px]
    pub const MULTI_LINE_HEIGHT: i16 = 60;

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

    fn new_instruction_internal<T: Into<TString<'static>>>(
        text: T,
        text_color: Color,
        icon: Option<Icon>,
        icon_color: Option<Color>,
    ) -> Self {
        let instruction_component = Instruction::new(text.into(), text_color, icon, icon_color);
        Self::from_content(HintContent::Instruction(instruction_component))
    }

    pub fn new_instruction<T: Into<TString<'static>>>(text: T, icon: Option<Icon>) -> Self {
        Self::new_instruction_internal(text, theme::GREY, icon, Some(theme::GREY_LIGHT))
    }
    pub fn new_instruction_green<T: Into<TString<'static>>>(text: T, icon: Option<Icon>) -> Self {
        Self::new_instruction_internal(text, theme::GREEN_LIME, icon, Some(theme::GREEN_LIME))
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

    pub fn update_page(&mut self, current: usize, max: usize) {
        match &mut self.content {
            HintContent::PageCounter(counter) => {
                counter.update_current_page(current, max);
                self.swipe_allow_down = counter.is_first_page();
                self.swipe_allow_up = counter.is_last_page();
            }
            _ => {
                #[cfg(feature = "ui_debug")]
                panic!("hint component does not have counter")
            }
        }
    }

    pub fn height(&self) -> i16 {
        self.content.height()
    }
}

impl<'a> Component for Hint<'a> {
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        debug_assert!(bounds.height() == self.content.height());
        self.area = bounds;
        self.area
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        match event {
            Event::Attach(_) => {
                self.progress = 0;
            }
            Event::Swipe(SwipeEvent::Move(dir, progress)) => match dir {
                Direction::Up if self.swipe_allow_up => {
                    self.progress = progress;
                    self.dir = dir;
                }
                Direction::Down if self.swipe_allow_down => {
                    self.progress = progress;
                    self.dir = dir;
                }
                _ => {}
            },
            _ => {}
        };

        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        let progress = self.progress as f32 / 1000.0;

        let shift = pareen::constant(0.0).seq_ease_out(
            0.0,
            easer::functions::Cubic,
            1.0,
            pareen::constant(1.0),
        );

        let offset = i16::lerp(0, 20, shift.eval(progress));

        let mask = u8::lerp(0, 255, shift.eval(progress));

        let offset = match self.dir {
            Direction::Up => Offset::y(-offset),
            Direction::Down => Offset::y(3 * offset),
            _ => Offset::zero(),
        };

        target.with_origin(offset, &|target| {
            self.content.render(self.area, target);
            shape::Bar::new(self.area)
                .with_alpha(mask)
                .with_fg(Color::black())
                .with_bg(Color::black())
                .render(target);
        });
    }
}

impl<'a> HintContent<'a> {
    fn height(&self) -> i16 {
        if matches!(self, HintContent::PageCounter(_)) {
            Hint::SINGLE_LINE_HEIGHT
        } else {
            // TODO: determine height based on text length
            Hint::MULTI_LINE_HEIGHT
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
    text: TString<'a>,
    text_color: Color,
    icon: Option<Icon>,
    icon_color: Option<Color>,
}

impl<'a> Instruction<'a> {
    const STYLE_INSTRUCTION: &'static TextStyle = &theme::TEXT_NORMAL;

    fn new(
        text: TString<'a>,
        text_color: Color,
        icon: Option<Icon>,
        icon_color: Option<Color>,
    ) -> Self {
        Self {
            text,
            text_color,
            icon,
            icon_color,
        }
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>, area: Rect) {
        const ICON_OFFSET: Offset = Offset::x(24);
        let text_baseline = if let Some(icon) = self.icon {
            let offset_x = Offset::x(icon.toif.width() + ICON_OFFSET.x);
            let icon_color = self.icon_color.unwrap_or(self.text_color);
            shape::ToifImage::new(area.top_left(), icon.toif)
                .with_align(Alignment2D::TOP_LEFT)
                .with_fg(self.text_color)
                .render(target);
            area.bottom_left() + offset_x
        } else {
            area.bottom_left()
        };
        self.text.map(|t| {
            Text::new(text_baseline, t)
                .with_font(Self::STYLE_INSTRUCTION.text_font)
                .with_fg(self.text_color)
                .with_align(Alignment::Start)
                .render(target)
        });
    }
}

/// Helper component used within Hint for page count indication, rendered e.g.
/// as: '1 / 20'.
#[derive(Clone)]
struct PageCounter {
    page_curr: u8,
    page_max: u8,
}

impl PageCounter {
    fn new() -> Self {
        Self {
            page_curr: 0,
            page_max: 0,
        }
    }

    fn update_current_page(&mut self, new_value: usize, max: usize) {
        self.page_max = max as u8;
        self.page_curr = (new_value as u8).clamp(0, self.page_max.saturating_sub(1));
    }

    fn is_first_page(&self) -> bool {
        self.page_curr == 0
    }

    fn is_last_page(&self) -> bool {
        self.page_curr + 1 == self.page_max
    }
}

impl PageCounter {
    fn render<'s>(&'s self, target: &mut impl Renderer<'s>, area: Rect) {
        let font = Font::SUB;
        let (color_num, color_icon) = if self.is_last_page() {
            (theme::GREEN_LIGHT, theme::GREEN)
        } else {
            (theme::GREY, theme::GREY_DARK)
        };

        let string_curr = uformat!("{}", self.page_curr + 1);
        let string_max = uformat!("{}", self.page_max);

        // the counter is left aligned
        let offset_x = Offset::x(4); // spacing between foreslash and numbers
        let width_num_curr = font.text_width(&string_curr);
        let width_foreslash = theme::ICON_FORESLASH.toif.width();
        let width_num_max = font.text_width(&string_max);
        let width_total = width_num_curr + width_foreslash + width_num_max + 2 * offset_x.x;

        let counter_area = area;
        let counter_start_x = counter_area.bottom_left().x;
        let counter_y = font.vert_center(counter_area.y0, counter_area.y1, "0");
        let counter_end_x = counter_start_x + width_total;
        let base_num_curr = Point::new(counter_start_x, counter_y);
        let base_foreslash = Point::new(counter_start_x + width_num_curr + offset_x.x, counter_y);
        let base_num_max = Point::new(counter_end_x, counter_y);

        Text::new(base_num_curr, &string_curr)
            .with_align(Alignment::Start)
            .with_fg(color_num)
            .with_font(font)
            .render(target);
        shape::ToifImage::new(base_foreslash, theme::ICON_FORESLASH.toif)
            .with_align(Alignment2D::BOTTOM_LEFT)
            .with_fg(color_icon)
            .render(target);
        Text::new(base_num_max, &string_max)
            .with_align(Alignment::End)
            .with_fg(color_num)
            .with_font(font)
            .render(target);
    }
}

#[cfg(feature = "ui_debug")]
impl<'a> crate::trace::Trace for Hint<'a> {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("Hint");
        match &self.content {
            HintContent::Instruction(i) => {
                t.string("instruction", i.text);
            }
            HintContent::PageCounter(counter) => {
                t.int("page curr", counter.page_curr.into());
                t.int("page max", counter.page_max.into());
            }
        }
    }
}
