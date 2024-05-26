use crate::{
    strutil::TString,
    ui::{
        component::{
            base::SwipeEvent, text::TextStyle, Component, Event, EventCtx, Never, SwipeDirection,
        },
        display::Color,
        geometry::{Alignment, Offset, Rect},
        lerp::Lerp,
        model_mercury::theme,
        shape,
        shape::{Renderer, Text},
    },
};

/// Component showing a task instruction (e.g. "Swipe up") and optionally task
/// description (e.g. "Confirm transaction") to a user. A host of this component
/// is responsible of providing the exact area considering also the spacing. The
/// height must be 18px (only instruction) or 37px (both description and
/// instruction). The content and style of both description and instruction is
/// configurable separatedly.
#[derive(Clone)]
pub struct Footer<'a> {
    area: Rect,
    text_instruction: TString<'a>,
    text_description: Option<TString<'a>>,
    style_instruction: &'static TextStyle,
    style_description: &'static TextStyle,
    swipe_allow_up: bool,
    swipe_allow_down: bool,
    progress: i16,
    dir: SwipeDirection,
}

impl<'a> Footer<'a> {
    /// height of the component with only instruction [px]
    pub const HEIGHT_SIMPLE: i16 = 18;
    /// height of the component with both description and instruction [px]
    pub const HEIGHT_DEFAULT: i16 = 37;

    pub fn new<T: Into<TString<'a>>>(instruction: T) -> Self {
        Self {
            area: Rect::zero(),
            text_instruction: instruction.into(),
            text_description: None,
            style_instruction: &theme::TEXT_SUB_GREY,
            style_description: &theme::TEXT_SUB_GREY_LIGHT,
            swipe_allow_down: false,
            swipe_allow_up: false,
            progress: 0,
            dir: SwipeDirection::Up,
        }
    }

    pub fn with_description<T: Into<TString<'a>>>(self, description: T) -> Self {
        Self {
            text_description: Some(description.into()),
            ..self
        }
    }

    pub fn update_instruction<T: Into<TString<'a>>>(&mut self, ctx: &mut EventCtx, s: T) {
        self.text_instruction = s.into();
        ctx.request_paint();
    }

    pub fn update_description<T: Into<TString<'a>>>(&mut self, ctx: &mut EventCtx, s: T) {
        self.text_description = Some(s.into());
        ctx.request_paint();
    }

    pub fn update_instruction_style(&mut self, ctx: &mut EventCtx, style: &'static TextStyle) {
        self.style_instruction = style;
        ctx.request_paint();
    }

    pub fn update_description_style(&mut self, ctx: &mut EventCtx, style: &'static TextStyle) {
        self.style_description = style;
        ctx.request_paint();
    }

    pub fn height(&self) -> i16 {
        if self.text_description.is_some() {
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
        self.area = bounds;
        bounds
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
        // TODO: remove when ui-t3t1 done
        todo!()
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
            // show description only if there is space for it
            if self.area.height() == Footer::HEIGHT_DEFAULT {
                if let Some(description) = self.text_description {
                    let area_description = self.area.split_top(Footer::HEIGHT_SIMPLE).0;
                    let text_description_font_descent = self
                        .style_description
                        .text_font
                        .visible_text_height_ex("Ay")
                        .1;
                    let text_description_baseline =
                        area_description.bottom_center() - Offset::y(text_description_font_descent);

                    description.map(|t| {
                        Text::new(text_description_baseline, t)
                            .with_font(self.style_description.text_font)
                            .with_fg(self.style_description.text_color)
                            .with_align(Alignment::Center)
                            .render(target);
                    });
                }
            }

            let area_instruction = self.area.split_bottom(Footer::HEIGHT_SIMPLE).1;
            let text_instruction_font_descent = self
                .style_instruction
                .text_font
                .visible_text_height_ex("Ay")
                .1;
            let text_instruction_baseline =
                area_instruction.bottom_center() - Offset::y(text_instruction_font_descent);
            self.text_instruction.map(|t| {
                Text::new(text_instruction_baseline, t)
                    .with_font(self.style_instruction.text_font)
                    .with_fg(self.style_instruction.text_color)
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
        if let Some(description) = self.text_description {
            t.string("description", description);
        }
        t.string("instruction", self.text_instruction);
    }
}
