use crate::{
    micropython::buffer::StrBuffer,
    time::{Duration, Instant},
    ui::{
        animation::Animation,
        component::{Component, Event, EventCtx},
        display::{self, Color, Font},
        geometry::{Offset, Rect},
        model_tr::theme,
        util::animation_disabled,
    },
};

pub enum LoaderMsg {
    GrownCompletely,
    ShrunkCompletely,
}

enum State {
    Initial,
    Growing(Animation<u16>),
    Shrinking(Animation<u16>),
    Grown,
}

pub struct Loader {
    area: Rect,
    state: State,
    growing_duration: Duration,
    shrinking_duration: Duration,
    text_overlay: display::TextOverlay<StrBuffer>,
    styles: LoaderStyleSheet,
}

impl Loader {
    pub const SIZE: Offset = Offset::new(120, 120);

    pub fn new(text_overlay: display::TextOverlay<StrBuffer>, styles: LoaderStyleSheet) -> Self {
        Self {
            area: Rect::zero(),
            state: State::Initial,
            growing_duration: Duration::from_millis(1000),
            shrinking_duration: Duration::from_millis(500),
            text_overlay,
            styles,
        }
    }

    pub fn text(text: StrBuffer, styles: LoaderStyleSheet) -> Self {
        let text_overlay = display::TextOverlay::new(text, styles.normal.font);

        Self::new(text_overlay, styles)
    }

    pub fn with_growing_duration(mut self, growing_duration: Duration) -> Self {
        self.growing_duration = growing_duration;
        self
    }

    /// Change the duration of the loader.
    pub fn set_duration(&mut self, growing_duration: Duration) {
        self.growing_duration = growing_duration;
    }

    pub fn get_duration(&self) -> Duration {
        self.growing_duration
    }

    pub fn get_text(&self) -> &StrBuffer {
        self.text_overlay.get_text()
    }

    /// Change the text of the loader.
    pub fn set_text(&mut self, text: StrBuffer) {
        self.text_overlay.set_text(text);
    }

    /// Return width of given text according to current style.
    pub fn get_text_width(&self, text: StrBuffer) -> i16 {
        self.styles.normal.font.text_width(text.as_ref())
    }

    pub fn start_growing(&mut self, ctx: &mut EventCtx, now: Instant) {
        let mut anim = Animation::new(
            display::LOADER_MIN,
            display::LOADER_MAX,
            self.growing_duration,
            now,
        );
        if let State::Shrinking(shrinking) = &self.state {
            anim.seek_to_value(shrinking.value(now));
        }
        self.state = State::Growing(anim);

        // The animation is starting, request an animation frame event.
        ctx.request_anim_frame();

        // We don't have to wait for the animation frame event with the first paint,
        // let's do that now.
        ctx.request_paint();
    }

    pub fn start_shrinking(&mut self, ctx: &mut EventCtx, now: Instant) {
        let mut anim = Animation::new(
            display::LOADER_MAX,
            display::LOADER_MIN,
            self.shrinking_duration,
            now,
        );
        if let State::Growing(growing) = &self.state {
            anim.seek_to_value(display::LOADER_MAX - growing.value(now));
        }
        self.state = State::Shrinking(anim);

        // The animation should be already progressing at this point, so we don't need
        // to request another animation frames, but we should request to get painted
        // after this event pass.
        ctx.request_paint();
    }

    pub fn reset(&mut self) {
        self.state = State::Initial;
    }

    pub fn animation(&self) -> Option<&Animation<u16>> {
        match &self.state {
            State::Initial => None,
            State::Grown => None,
            State::Growing(a) | State::Shrinking(a) => Some(a),
        }
    }

    pub fn progress(&self, now: Instant) -> Option<u16> {
        self.animation().map(|a| a.value(now))
    }

    pub fn is_animating(&self) -> bool {
        self.animation().is_some()
    }

    pub fn is_completely_grown(&self, now: Instant) -> bool {
        matches!(self.progress(now), Some(display::LOADER_MAX))
    }

    pub fn is_completely_shrunk(&self, now: Instant) -> bool {
        matches!(self.progress(now), Some(display::LOADER_MIN))
    }

    pub fn paint_loader(&mut self, style: &LoaderStyle, done: i32) {
        // NOTE: need to calculate this in `i32`, it would overflow using `i16`
        let invert_from = ((self.area.width() as i32 + 1) * done) / (display::LOADER_MAX as i32);

        display::bar_with_text_and_fill(
            self.area,
            Some(&self.text_overlay),
            style.fg_color,
            style.bg_color,
            -1,
            invert_from as i16,
        );
    }
}

impl Component for Loader {
    type Msg = LoaderMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.area = bounds;
        // Centering the text in the loader rectangle.
        let baseline = bounds.bottom_center() + Offset::new(1, -2);
        self.text_overlay.place(baseline);
        self.area
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        let now = Instant::now();

        if let Event::Timer(EventCtx::ANIM_FRAME_TIMER) = event {
            if self.is_animating() {
                if self.is_completely_grown(now) {
                    self.state = State::Grown;
                    ctx.request_paint();
                    return Some(LoaderMsg::GrownCompletely);
                } else if self.is_completely_shrunk(now) {
                    self.state = State::Initial;
                    ctx.request_paint();
                    return Some(LoaderMsg::ShrunkCompletely);
                } else {
                    // There is further progress in the animation, request an animation frame event.
                    ctx.request_anim_frame();
                    // We have something to paint, so request to be painted in the next pass.
                    if !animation_disabled() {
                        ctx.request_paint();
                    }
                }
            }
        }
        None
    }

    fn paint(&mut self) {
        // TODO: Consider passing the current instant along with the event -- that way,
        // we could synchronize painting across the component tree. Also could be useful
        // in automated tests.
        // In practice, taking the current instant here is more precise in case some
        // other component in the tree takes a long time to draw.
        let now = Instant::now();

        if let State::Initial = self.state {
            self.paint_loader(self.styles.normal, 0);
        } else if let State::Grown = self.state {
            self.paint_loader(self.styles.normal, display::LOADER_MAX as i32);
        } else {
            let progress = self.progress(now);
            if let Some(done) = progress {
                self.paint_loader(self.styles.normal, done as i32);
            } else {
                self.paint_loader(self.styles.normal, 0);
            }
        }
    }
}

pub struct LoaderStyleSheet {
    pub normal: &'static LoaderStyle,
}

pub struct LoaderStyle {
    pub font: Font,
    pub fg_color: Color,
    pub bg_color: Color,
}

impl LoaderStyleSheet {
    pub fn default() -> Self {
        Self {
            normal: &LoaderStyle {
                font: theme::FONT_BUTTON,
                fg_color: theme::FG,
                bg_color: theme::BG,
            },
        }
    }
}

// DEBUG-ONLY SECTION BELOW

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for Loader {
    fn trace(&self, d: &mut dyn crate::trace::Tracer) {
        d.open("Loader");
        d.close();
    }
}
