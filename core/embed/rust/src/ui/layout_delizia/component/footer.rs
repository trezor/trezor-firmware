use sys::time::Instant;

use super::super::fonts::FONT_SUB;
use super::{theme, Button, ButtonMsg};
use crate::strutil::TString;
use crate::ui::component::text::TextStyle;
use crate::ui::component::{Component, Event, EventCtx, Marquee};
use crate::ui::display::{Color, Font};
use crate::ui::event::SwipeEvent;
use crate::ui::geometry::{Alignment, Alignment2D, Direction, Insets, Offset, Point, Rect};
use crate::ui::lerp::Lerp;
use crate::ui::shape::{self, Renderer, Text};
use crate::ui::util::Pager;
use crate::ui::{CommonUI, ModelUI};

/// Component showing a task instruction, e.g. "Swipe up", and an optional
/// content consisting of one of these:
///     - a task description e.g. "Confirm transaction", or
///     - a page counter e.g. "1 / 3", meaning the first screen of three total,
///       or
///     - a page hint e.g. "Go back" if you are on the last page.
/// A host of this component is responsible of providing the exact area
/// considering also the spacing. The height must be 18px (only instruction) or
/// 37px (instruction and description/position).
/// The instruction and description texts are rendered by a `Marquee` so that
/// they scroll back and forth when they do not fit the available width.
pub struct Footer {
    area: Rect,
    content: FooterContent,
    swipe_allow_up: bool,
    swipe_allow_down: bool,
    progress: i16,
    dir: Direction,
    virtual_button: Button,
}

enum FooterContent {
    Instruction(Marquee),
    InstructionDescription(Marquee, Marquee),
    PageCounter(PageCounter),
    PageHint(PageHint),
}

impl Footer {
    /// height of the component with only instruction [px]
    pub const HEIGHT_SIMPLE: i16 = 18;
    /// height of the component with instruction and additional content [px]
    pub const HEIGHT_DEFAULT: i16 = 37;

    const STYLE_INSTRUCTION: &'static TextStyle = &theme::TEXT_SUB_GREY;
    const STYLE_DESCRIPTION: &'static TextStyle = &theme::TEXT_SUB_GREY_LIGHT;

    fn from_content(content: FooterContent) -> Self {
        Self {
            area: Rect::zero(),
            content,
            swipe_allow_down: false,
            swipe_allow_up: false,
            progress: 0,
            dir: Direction::Up,
            virtual_button: Button::empty(),
        }
    }

    fn set_marquee_text(marquee: &mut Marquee, ctx: &mut EventCtx, text: TString<'static>) {
        marquee.set_text(text);
        marquee.reset();
        marquee.start(ctx, Instant::now());
    }

    pub fn new<T: Into<TString<'static>>>(
        instruction: T,
        description: Option<TString<'static>>,
    ) -> Self {
        let instruction = FooterContent::instruction_marquee(instruction.into());
        let content = match description {
            Some(d) => FooterContent::InstructionDescription(
                instruction,
                FooterContent::description_marquee(d),
            ),
            None => FooterContent::Instruction(instruction),
        };
        Self::from_content(content)
    }

    pub fn with_page_counter(instruction: TString<'static>) -> Self {
        Self::from_content(FooterContent::PageCounter(PageCounter::new(instruction)))
    }

    pub fn with_page_hint(
        description: TString<'static>,
        description_last: TString<'static>,
        instruction: TString<'static>,
        instruction_last: TString<'static>,
    ) -> Self {
        Self::from_content(FooterContent::PageHint(PageHint {
            description,
            description_last,
            instruction,
            instruction_last,
            // The texts are empty until the pager is updated, same as the
            // behavior of `Pager::single_page()`.
            description_marquee: FooterContent::description_marquee(TString::empty()),
            instruction_marquee: FooterContent::instruction_marquee(TString::empty()),
            pager: Pager::single_page(),
        }))
    }

    pub fn update_instruction<T: Into<TString<'static>>>(&mut self, ctx: &mut EventCtx, s: T) {
        match &mut self.content {
            FooterContent::Instruction(i) => Self::set_marquee_text(i, ctx, s.into()),
            FooterContent::InstructionDescription(i, _d) => {
                Self::set_marquee_text(i, ctx, s.into())
            }
            FooterContent::PageCounter(page_counter) => page_counter.instruction = s.into(),
            _ => {
                #[cfg(feature = "ui_debug")]
                panic!("not supported")
            }
        }
        ctx.request_paint();
    }

    pub fn update_description<T: Into<TString<'static>>>(&mut self, ctx: &mut EventCtx, s: T) {
        if let FooterContent::InstructionDescription(_i, d) = &mut self.content {
            Self::set_marquee_text(d, ctx, s.into());
            ctx.request_paint();
        } else {
            #[cfg(feature = "ui_debug")]
            panic!("footer does not have description")
        }
    }

    pub fn update_pager(&mut self, ctx: &mut EventCtx, pager: Pager) {
        match &mut self.content {
            FooterContent::PageCounter(counter) => {
                counter.update(pager);
                self.swipe_allow_down = pager.is_first();
                self.swipe_allow_up = pager.is_last();
                ctx.request_paint();
            }
            FooterContent::PageHint(hint) => {
                hint.update(ctx, pager);
                self.swipe_allow_down = pager.is_first();
                self.swipe_allow_up = pager.is_last();
                ctx.request_paint();
            }
            _ => {
                #[cfg(feature = "ui_debug")]
                panic!("footer does not have counter")
            }
        }
    }

    pub fn height(&self) -> i16 {
        self.content.height()
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
}

impl Component for Footer {
    type Msg = ();

    fn place(&mut self, bounds: Rect) -> Rect {
        // place the button over bottom 2/3 of the screen
        let button_area = ModelUI::SCREEN.inset(Insets::top(ModelUI::SCREEN.height() / 3));
        self.virtual_button.place(button_area);

        assert!(bounds.height() == self.content.height());
        self.area = bounds;
        self.content.place(bounds);
        self.area
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        let btn_event = self.virtual_button.event(ctx, event);
        self.content.event(ctx, event);
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

        match btn_event {
            Some(ButtonMsg::Clicked) => Some(()),
            _ => None,
        }
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        let progress = f32::from(self.progress) / 1000.0;

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

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for Footer {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("Footer");
        match &self.content {
            FooterContent::Instruction(i) => {
                t.string("instruction", i.text());
            }
            FooterContent::InstructionDescription(i, d) => {
                t.string("description", d.text());
                t.string("instruction", i.text());
            }
            FooterContent::PageCounter(counter) => counter.trace(t),
            FooterContent::PageHint(page_hint) => {
                t.string("description", page_hint.description());
                t.string("instruction", page_hint.instruction());
            }
        }
    }
}

impl FooterContent {
    fn height(&self) -> i16 {
        if matches!(self, FooterContent::Instruction(_)) {
            Footer::HEIGHT_SIMPLE
        } else {
            Footer::HEIGHT_DEFAULT
        }
    }

    fn instruction_marquee(text: TString<'static>) -> Marquee {
        Marquee::new(
            text,
            Footer::STYLE_INSTRUCTION.text_font,
            Footer::STYLE_INSTRUCTION.text_color,
            theme::BG,
        )
        .with_alignment(Alignment::Center)
    }

    fn description_marquee(text: TString<'static>) -> Marquee {
        Marquee::new(
            text,
            Footer::STYLE_DESCRIPTION.text_font,
            Footer::STYLE_DESCRIPTION.text_color,
            theme::BG,
        )
        .with_alignment(Alignment::Center)
    }

    /// Area of a `Marquee` rendering text previously drawn at the bottom of
    /// `strip`: `Marquee` renders the text baseline at `text_height - 1`
    /// below the top of its area, so the area is shifted upwards such that
    /// the baseline matches the original text position. The bottom of the
    /// area is kept at the bottom of the strip so that descenders are not
    /// clipped.
    fn marquee_area(strip: Rect, font: Font) -> Rect {
        let descent = font.visible_text_height_ex("Ay").1;
        let top = strip.y1 - descent - (font.text_height() - 1);
        Rect::from_top_left_and_size(
            Point::new(strip.x0, top),
            Offset::new(strip.width(), strip.y1 - top),
        )
    }

    fn instruction_marquee_area(area: Rect) -> Rect {
        let strip = area.split_bottom(Footer::HEIGHT_SIMPLE).1;
        Self::marquee_area(strip, Footer::STYLE_INSTRUCTION.text_font)
    }

    fn description_marquee_area(area: Rect) -> Rect {
        let strip = area.split_top(Footer::HEIGHT_SIMPLE).0;
        Self::marquee_area(strip, Footer::STYLE_DESCRIPTION.text_font)
    }

    fn place(&mut self, area: Rect) {
        match self {
            FooterContent::Instruction(instruction) => {
                instruction.place(Self::instruction_marquee_area(area));
            }
            FooterContent::InstructionDescription(instruction, description) => {
                instruction.place(Self::instruction_marquee_area(area));
                description.place(Self::description_marquee_area(area));
            }
            FooterContent::PageCounter(_) => {}
            FooterContent::PageHint(page_hint) => {
                page_hint
                    .instruction_marquee
                    .place(Self::instruction_marquee_area(area));
                page_hint
                    .description_marquee
                    .place(Self::description_marquee_area(area));
            }
        }
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) {
        if let Event::Attach(_) = event {
            self.for_each_marquee(|m| m.start(ctx, Instant::now()));
        } else {
            self.for_each_marquee(|m| {
                m.event(ctx, event);
            });
        }
    }

    fn for_each_marquee(&mut self, mut f: impl FnMut(&mut Marquee)) {
        match self {
            FooterContent::Instruction(instruction) => f(instruction),
            FooterContent::InstructionDescription(instruction, description) => {
                f(instruction);
                f(description);
            }
            FooterContent::PageCounter(_) => {}
            FooterContent::PageHint(page_hint) => {
                f(&mut page_hint.instruction_marquee);
                f(&mut page_hint.description_marquee);
            }
        }
    }

    fn render<'s>(&'s self, area: Rect, target: &mut impl Renderer<'s>) {
        match self {
            FooterContent::Instruction(instruction) => {
                instruction.render(target);
            }
            FooterContent::InstructionDescription(instruction, description) => {
                description.render(target);
                instruction.render(target);
            }
            FooterContent::PageCounter(page_counter) => page_counter.render(target, area),
            FooterContent::PageHint(page_hint) => {
                page_hint.description_marquee.render(target);
                page_hint.instruction_marquee.render(target);
            }
        }
    }

    fn render_instruction<'s>(
        target: &mut impl Renderer<'s>,
        area: Rect,
        instruction: &TString<'static>,
    ) {
        let area_instruction = area.split_bottom(Footer::HEIGHT_SIMPLE).1;
        let text_instruction_font_descent = Footer::STYLE_INSTRUCTION
            .text_font
            .visible_text_height_ex("Ay")
            .1;
        let text_instruction_baseline =
            area_instruction.bottom_center() - Offset::y(text_instruction_font_descent);
        instruction.map(|t| {
            Text::new(
                text_instruction_baseline,
                t,
                Footer::STYLE_INSTRUCTION.text_font,
            )
            .with_fg(Footer::STYLE_INSTRUCTION.text_color)
            .with_align(Alignment::Center)
            .with_max_width(area_instruction.width())
            .render(target)
        });
    }
}

/// Helper component used within Footer instead of description for page count
/// indication, rendered e.g. as: '1 / 20'.
#[derive(Clone)]
struct PageCounter {
    pub instruction: TString<'static>,
    font: Font,
    pager: Pager,
}

impl PageCounter {
    fn new(instruction: TString<'static>) -> Self {
        Self {
            instruction,
            pager: Pager::single_page(),
            font: FONT_SUB,
        }
    }

    fn update(&mut self, pager: Pager) {
        self.pager = pager;
    }
}

impl PageCounter {
    fn render<'s>(&'s self, target: &mut impl Renderer<'s>, area: Rect) {
        let color = if self.pager.is_last() {
            theme::GREEN_LIGHT
        } else {
            theme::GREY_LIGHT
        };

        let string_curr = uformat!("{}", self.pager.current() + 1);
        let string_max = uformat!("{}", self.pager.total());

        // center the whole counter "x / yz"
        let offset_x = Offset::x(4); // spacing between foreslash and numbers
        let width_num_curr = self.font.text_width(&string_curr);
        let width_foreslash = theme::ICON_FORESLASH.toif.width();
        let width_num_max = self.font.text_width(&string_max);
        let width_total = width_num_curr + width_foreslash + width_num_max + 2 * offset_x.x;

        let counter_area = area.split_top(Footer::HEIGHT_SIMPLE).0;
        let center_x = counter_area.center().x;
        let counter_y = self.font.vert_center(counter_area.y0, counter_area.y1, "0");
        let counter_start_x = center_x - width_total / 2;
        let counter_end_x = center_x + width_total / 2;
        let base_num_curr = Point::new(counter_start_x, counter_y);
        let base_foreslash = Point::new(counter_start_x + width_num_curr + offset_x.x, counter_y);
        let base_num_max = Point::new(counter_end_x, counter_y);

        Text::new(base_num_curr, &string_curr, self.font)
            .with_align(Alignment::Start)
            .with_fg(color)
            .render(target);
        shape::ToifImage::new(base_foreslash, theme::ICON_FORESLASH.toif)
            .with_align(Alignment2D::BOTTOM_LEFT)
            .with_fg(color)
            .render(target);
        Text::new(base_num_max, &string_max, self.font)
            .with_align(Alignment::End)
            .with_fg(color)
            .render(target);

        FooterContent::render_instruction(target, area, &self.instruction);
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for PageCounter {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("PageCounter");
        t.int("page current", self.pager.current().into());
        t.int("page max", self.pager.total().into());
    }
}

struct PageHint {
    pub description: TString<'static>,
    pub description_last: TString<'static>,
    pub instruction: TString<'static>,
    pub instruction_last: TString<'static>,
    pub description_marquee: Marquee,
    pub instruction_marquee: Marquee,
    pub pager: Pager,
}

impl PageHint {
    fn update(&mut self, ctx: &mut EventCtx, pager: Pager) {
        self.pager = pager;
        let description = self.description();
        Footer::set_marquee_text(&mut self.description_marquee, ctx, description);
        let instruction = self.instruction();
        Footer::set_marquee_text(&mut self.instruction_marquee, ctx, instruction);
    }

    fn description(&self) -> TString<'static> {
        if self.pager.is_single() {
            TString::empty()
        } else if self.pager.is_last() {
            self.description_last
        } else {
            self.description
        }
    }

    fn instruction(&self) -> TString<'static> {
        if self.pager.is_single() {
            TString::empty()
        } else if self.pager.is_last() {
            self.instruction_last
        } else {
            self.instruction
        }
    }
}
