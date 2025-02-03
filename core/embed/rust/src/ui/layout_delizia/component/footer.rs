use crate::{
    strutil::TString,
    ui::{
        component::{text::TextStyle, Component, Event, EventCtx},
        display::{Color, Font},
        event::SwipeEvent,
        geometry::{Alignment, Alignment2D, Direction, Insets, Offset, Point, Rect},
        lerp::Lerp,
        shape::{self, Renderer, Text},
        util::Pager,
        CommonUI, ModelUI,
    },
};

use super::{super::fonts::FONT_SUB, theme, Button, ButtonMsg};

/// Component showing a task instruction, e.g. "Swipe up", and an optional
/// content consisting of one of these:
///     - a task description e.g. "Confirm transaction", or
///     - a page counter e.g. "1 / 3", meaning the first screen of three total.
/// A host of this component is responsible of providing the exact area
/// considering also the spacing. The height must be 18px (only instruction) or
/// 37px (instruction and description/position).
pub struct Footer<'a> {
    area: Rect,
    content: FooterContent<'a>,
    swipe_allow_up: bool,
    swipe_allow_down: bool,
    progress: i16,
    dir: Direction,
    virtual_button: Button,
}

#[derive(Clone)]
enum FooterContent<'a> {
    Instruction(TString<'a>),
    InstructionDescription(TString<'a>, TString<'a>),
    PageCounter(PageCounter),
    PageHint(PageHint),
}

impl<'a> Footer<'a> {
    /// height of the component with only instruction [px]
    pub const HEIGHT_SIMPLE: i16 = 18;
    /// height of the component with instruction and additional content [px]
    pub const HEIGHT_DEFAULT: i16 = 37;

    const STYLE_INSTRUCTION: &'static TextStyle = &theme::TEXT_SUB_GREY;
    const STYLE_DESCRIPTION: &'static TextStyle = &theme::TEXT_SUB_GREY_LIGHT;

    fn from_content(content: FooterContent<'a>) -> Self {
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

    pub fn new<T: Into<TString<'a>>>(
        instruction: T,
        description: Option<TString<'static>>,
    ) -> Self {
        let instruction = instruction.into();
        Self::from_content(
            description
                .map(|d| FooterContent::InstructionDescription(instruction, d))
                .unwrap_or(FooterContent::Instruction(instruction)),
        )
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
            pager: Pager::single_page(),
        }))
    }

    pub fn update_instruction<T: Into<TString<'static>>>(&mut self, ctx: &mut EventCtx, s: T) {
        match &mut self.content {
            FooterContent::Instruction(i) => *i = s.into(),
            FooterContent::InstructionDescription(i, _d) => *i = s.into(),
            FooterContent::PageCounter(page_counter) => page_counter.instruction = s.into(),
            _ => {
                #[cfg(feature = "ui_debug")]
                panic!("not supported")
            }
        }
        ctx.request_paint();
    }

    pub fn update_description<T: Into<TString<'a>>>(&mut self, ctx: &mut EventCtx, s: T) {
        if let FooterContent::InstructionDescription(_i, d) = &mut self.content {
            *d = s.into();
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
                hint.update(pager);
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

impl<'a> Component for Footer<'a> {
    type Msg = ();

    fn place(&mut self, bounds: Rect) -> Rect {
        // place the button over bottom 2/3 of the screen
        let button_area = ModelUI::SCREEN.inset(Insets::top(ModelUI::SCREEN.height() / 3));
        self.virtual_button.place(button_area);

        assert!(bounds.height() == self.content.height());
        self.area = bounds;
        self.area
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        let btn_event = self.virtual_button.event(ctx, event);
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

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for Footer<'_> {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("Footer");
        match &self.content {
            FooterContent::Instruction(i) => {
                t.string("instruction", *i);
            }
            FooterContent::InstructionDescription(i, d) => {
                t.string("description", *d);
                t.string("instruction", *i);
            }
            FooterContent::PageCounter(counter) => counter.trace(t),
            FooterContent::PageHint(page_hint) => {
                t.string("description", page_hint.description());
                t.string("instruction", page_hint.instruction());
            }
        }
    }
}

impl<'a> FooterContent<'a> {
    fn height(&self) -> i16 {
        if matches!(self, FooterContent::Instruction(_)) {
            Footer::HEIGHT_SIMPLE
        } else {
            Footer::HEIGHT_DEFAULT
        }
    }

    fn render<'s>(&'s self, area: Rect, target: &mut impl Renderer<'s>)
    where
        's: 'a,
    {
        match self {
            FooterContent::Instruction(instruction) => {
                Self::render_instruction(target, area, instruction);
            }
            FooterContent::InstructionDescription(instruction, description) => {
                Self::render_description(target, area, description);
                Self::render_instruction(target, area, instruction);
            }
            FooterContent::PageCounter(page_counter) => page_counter.render(target, area),
            FooterContent::PageHint(page_hint) => {
                Self::render_description(target, area, &page_hint.description());
                Self::render_instruction(target, area, &page_hint.instruction());
            }
        }
    }

    fn render_description<'s>(
        target: &mut impl Renderer<'s>,
        area: Rect,
        description: &TString<'a>,
    ) {
        let area_description = area.split_top(Footer::HEIGHT_SIMPLE).0;
        let text_description_font_descent = Footer::STYLE_DESCRIPTION
            .text_font
            .visible_text_height_ex("Ay")
            .1;
        let text_description_baseline =
            area_description.bottom_center() - Offset::y(text_description_font_descent);

        description.map(|t| {
            Text::new(
                text_description_baseline,
                t,
                Footer::STYLE_DESCRIPTION.text_font,
            )
            .with_fg(Footer::STYLE_DESCRIPTION.text_color)
            .with_align(Alignment::Center)
            .render(target)
        });
    }

    fn render_instruction<'s>(
        target: &mut impl Renderer<'s>,
        area: Rect,
        instruction: &TString<'a>,
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

#[derive(Clone)]
struct PageHint {
    pub description: TString<'static>,
    pub description_last: TString<'static>,
    pub instruction: TString<'static>,
    pub instruction_last: TString<'static>,
    pub pager: Pager,
}

impl PageHint {
    fn update(&mut self, pager: Pager) {
        self.pager = pager;
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
