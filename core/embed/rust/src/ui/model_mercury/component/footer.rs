use crate::{
    strutil::TString,
    ui::{
        component::{text::TextStyle, Component, Event, EventCtx, Never, SwipeDirection},
        display::{Color, Font},
        event::SwipeEvent,
        geometry::{Alignment, Alignment2D, Offset, Point, Rect},
        lerp::Lerp,
        model_mercury::theme,
        shape,
        shape::{Renderer, Text},
    },
};

/// Component showing a task instruction, e.g. "Swipe up", and an optional
/// content consisting of one of these:
///     - a task description e.g. "Confirm transaction", or
///     - a page counter e.g. "1 / 3", meaning the first screen of three total.
/// A host of this component is responsible of providing the exact area
/// considering also the spacing. The height must be 18px (only instruction) or
/// 37px (instruction and description/position).
#[derive(Clone)]
pub struct Footer<'a> {
    area: Rect,
    instruction: TString<'a>,
    content: Option<FooterContent<'a>>,
    swipe_allow_up: bool,
    swipe_allow_down: bool,
    progress: i16,
    dir: SwipeDirection,
}

#[derive(Clone)]
enum FooterContent<'a> {
    Description(TString<'a>),
    PageCounter(PageCounter),
}

impl<'a> Footer<'a> {
    /// height of the component with only instruction [px]
    pub const HEIGHT_SIMPLE: i16 = 18;
    /// height of the component with instruction and additional content [px]
    pub const HEIGHT_DEFAULT: i16 = 37;

    const STYLE_INSTRUCTION: &'static TextStyle = &theme::TEXT_SUB_GREY;
    const STYLE_DESCRIPTION: &'static TextStyle = &theme::TEXT_SUB_GREY_LIGHT;

    pub fn new<T: Into<TString<'a>>>(instruction: T) -> Self {
        Self {
            area: Rect::zero(),
            instruction: instruction.into(),
            content: None,
            swipe_allow_down: false,
            swipe_allow_up: false,
            progress: 0,
            dir: SwipeDirection::Up,
        }
    }

    pub fn with_description<T: Into<TString<'a>>>(self, description: T) -> Self {
        Self {
            content: Some(FooterContent::Description(description.into())),
            ..self
        }
    }

    pub fn with_page_counter(self, max_pages: u8) -> Self {
        Self {
            content: Some(FooterContent::PageCounter(PageCounter::new(max_pages))),
            ..self
        }
    }

    pub fn update_instruction<T: Into<TString<'a>>>(&mut self, ctx: &mut EventCtx, s: T) {
        self.instruction = s.into();
        ctx.request_paint();
    }

    pub fn update_description<T: Into<TString<'a>>>(&mut self, ctx: &mut EventCtx, s: T) {
        if let Some(ref mut content) = self.content {
            if let Some(text) = content.as_description_mut() {
                *text = s.into();
                ctx.request_paint();
            } else {
                #[cfg(feature = "ui_debug")]
                panic!("footer does not have description")
            }
        }
    }

    pub fn update_page_counter(&mut self, ctx: &mut EventCtx, n: u8) {
        if let Some(ref mut content) = self.content {
            if let Some(counter) = content.as_page_counter_mut() {
                counter.update_current_page(n);
                self.swipe_allow_down = counter.is_first_page();
                self.swipe_allow_up = counter.is_last_page();
                ctx.request_paint();
            } else {
                #[cfg(feature = "ui_debug")]
                panic!("footer does not have counter")
            }
        }
    }

    pub fn height(&self) -> i16 {
        if self.content.is_some() {
            Footer::HEIGHT_DEFAULT
        } else {
            Footer::HEIGHT_SIMPLE
        }
    }

    pub fn with_swipe_up(self) -> Self {
        Self {
            swipe_allow_up: true,
            ..self
        }
    }
    pub fn with_swipe_down(self) -> Self {
        Self {
            swipe_allow_down: true,
            ..self
        }
    }
}

impl<'a> Component for Footer<'a> {
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        let h = bounds.height();
        assert!(h == Footer::HEIGHT_SIMPLE || h == Footer::HEIGHT_DEFAULT);
        if let Some(content) = &mut self.content {
            if let Some(counter) = content.as_page_counter_mut() {
                if h == Footer::HEIGHT_DEFAULT {
                    counter.place(bounds.split_top(Footer::HEIGHT_SIMPLE).0);
                }
            }
        }
        self.area = bounds;
        self.area
    }

    fn event(&mut self, _ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        match event {
            Event::Attach(_) => {
                self.progress = 0;
            }
            Event::Swipe(SwipeEvent::Move(dir, progress)) => match dir {
                SwipeDirection::Up => {
                    if self.swipe_allow_up {
                        self.progress = progress;
                        self.dir = dir;
                    }
                }
                SwipeDirection::Down => {
                    if self.swipe_allow_down {
                        self.progress = progress;
                        self.dir = dir;
                    }
                }
                _ => {}
            },
            _ => {}
        };

        None
    }

    fn paint(&mut self) {
        todo!("remove when ui-t3t1 done")
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
            SwipeDirection::Up => Offset::y(-offset),
            SwipeDirection::Down => Offset::y(3 * offset),
            _ => Offset::zero(),
        };

        target.with_origin(offset, &|target| {
            // show description/counter only if there is space for it
            if self.area.height() == Footer::HEIGHT_DEFAULT {
                if let Some(content) = &self.content {
                    match content {
                        FooterContent::Description(text) => {
                            let area_description = self.area.split_top(Footer::HEIGHT_SIMPLE).0;
                            let text_description_font_descent = Footer::STYLE_DESCRIPTION
                                .text_font
                                .visible_text_height_ex("Ay")
                                .1;
                            let text_description_baseline = area_description.bottom_center()
                                - Offset::y(text_description_font_descent);

                            text.map(|t| {
                                Text::new(text_description_baseline, t)
                                    .with_font(Footer::STYLE_DESCRIPTION.text_font)
                                    .with_fg(Footer::STYLE_DESCRIPTION.text_color)
                                    .with_align(Alignment::Center)
                                    .render(target);
                            });
                        }
                        FooterContent::PageCounter(counter) => {
                            counter.render(target);
                        }
                    }
                }
            }

            let area_instruction = self.area.split_bottom(Footer::HEIGHT_SIMPLE).1;
            let text_instruction_font_descent = Footer::STYLE_INSTRUCTION
                .text_font
                .visible_text_height_ex("Ay")
                .1;
            let text_instruction_baseline =
                area_instruction.bottom_center() - Offset::y(text_instruction_font_descent);
            self.instruction.map(|t| {
                Text::new(text_instruction_baseline, t)
                    .with_font(Footer::STYLE_INSTRUCTION.text_font)
                    .with_fg(Footer::STYLE_INSTRUCTION.text_color)
                    .with_align(Alignment::Center)
                    .render(target);
            });

            shape::Bar::new(self.area)
                .with_alpha(mask)
                .with_fg(Color::black())
                .with_bg(Color::black())
                .render(target);
        });
    }

    #[cfg(feature = "ui_bounds")]
    fn bounds(&self, sink: &mut dyn FnMut(Rect)) {
        sink(self.area);
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for Footer<'_> {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("Footer");
        if let Some(content) = &self.content {
            match content {
                FooterContent::Description(text) => t.string("description", *text),
                FooterContent::PageCounter(counter) => counter.trace(t),
            }
        }
        t.string("instruction", self.instruction);
    }
}

impl<'a> FooterContent<'a> {
    pub fn as_description_mut(&mut self) -> Option<&mut TString<'a>> {
        match self {
            FooterContent::Description(ref mut text) => Some(text),
            _ => None,
        }
    }

    pub fn as_page_counter_mut(&mut self) -> Option<&mut PageCounter> {
        match self {
            FooterContent::PageCounter(ref mut counter) => Some(counter),
            _ => None,
        }
    }
}

/// Helper component used within Footer instead of description for page count
/// indication, rendered e.g. as: '1 / 20'.
#[derive(Clone)]
struct PageCounter {
    area: Rect,
    font: Font,
    page_curr: u8,
    page_max: u8,
}

impl PageCounter {
    fn new(page_max: u8) -> Self {
        Self {
            area: Rect::zero(),
            page_curr: 1,
            page_max,
            font: Font::SUB,
        }
    }

    fn update_current_page(&mut self, new_value: u8) {
        self.page_curr = new_value.clamp(1, self.page_max);
    }

    fn is_first_page(&self) -> bool {
        self.page_curr == 1
    }

    fn is_last_page(&self) -> bool {
        self.page_curr == self.page_max
    }
}

impl Component for PageCounter {
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.area = bounds;
        self.area
    }

    fn event(&mut self, _ctx: &mut EventCtx, _event: Event) -> Option<Self::Msg> {
        None
    }

    fn paint(&mut self) {
        todo!("remove when ui-t3t1 done")
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        let color = if self.page_curr == self.page_max {
            theme::GREEN_LIGHT
        } else {
            theme::GREY_LIGHT
        };

        let string_curr = uformat!("{}", self.page_curr);
        let string_max = uformat!("{}", self.page_max);

        // center the whole counter "x / yz"
        let offset_x = Offset::x(4); // spacing between foreslash and numbers
        let width_num_curr = self.font.text_width(&string_curr);
        let width_foreslash = theme::ICON_FORESLASH.toif.width();
        let width_num_max = self.font.text_width(&string_max);
        let width_total = width_num_curr + width_foreslash + width_num_max + 2 * offset_x.x;

        let center_x = self.area.center().x;
        let counter_y = self.font.vert_center(self.area.y0, self.area.y1, "0");
        let counter_start_x = center_x - width_total / 2;
        let counter_end_x = center_x + width_total / 2;
        let base_num_curr = Point::new(counter_start_x, counter_y);
        let base_foreslash = Point::new(counter_start_x + width_num_curr + offset_x.x, counter_y);
        let base_num_max = Point::new(counter_end_x, counter_y);

        Text::new(base_num_curr, &string_curr)
            .with_align(Alignment::Start)
            .with_fg(color)
            .with_font(self.font)
            .render(target);
        shape::ToifImage::new(base_foreslash, theme::ICON_FORESLASH.toif)
            .with_align(Alignment2D::BOTTOM_LEFT)
            .with_fg(color)
            .render(target);
        Text::new(base_num_max, &string_max)
            .with_align(Alignment::End)
            .with_fg(color)
            .with_font(self.font)
            .render(target);
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for PageCounter {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("PageCounter");
        t.int("page current", self.page_curr.into());
        t.int("page max", self.page_max.into());
    }
}
