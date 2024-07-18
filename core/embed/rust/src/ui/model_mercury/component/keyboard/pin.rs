use core::mem;

use crate::{
    strutil::{ShortString, TString},
    time::{Duration, Stopwatch},
    trezorhal::random,
    ui::{
        component::{
            base::{AttachType, ComponentExt},
            text::TextStyle,
            Component, Event, EventCtx, Label, Never, Pad, SwipeDirection, TimerToken,
        },
        display::Font,
        event::TouchEvent,
        geometry::{Alignment, Alignment2D, Grid, Insets, Offset, Rect},
        model_mercury::{
            component::{
                button::{
                    Button, ButtonContent,
                    ButtonMsg::{self, Clicked},
                },
                theme,
            },
            cshape,
        },
        shape::{self, Renderer},
        util::animation_disabled,
    },
};

pub enum PinKeyboardMsg {
    Confirmed,
    Cancelled,
}

const MAX_LENGTH: usize = 50;
const MAX_VISIBLE_DOTS: usize = 18;
const MAX_VISIBLE_DIGITS: usize = 18;
const DIGIT_COUNT: usize = 10; // 0..10

const HEADER_PADDING_TOP: i16 = 4;
const HEADER_PADDING_SIDE: i16 = 2;
const HEADER_PADDING_BOTTOM: i16 = 4;

const HEADER_PADDING: Insets = Insets::new(
    HEADER_PADDING_TOP,
    HEADER_PADDING_SIDE,
    HEADER_PADDING_BOTTOM,
    HEADER_PADDING_SIDE,
);

#[derive(Default, Clone)]
struct AttachAnimation {
    pub attach_top: bool,
    pub timer: Stopwatch,
    pub active: bool,
    pub duration: Duration,
}

impl AttachAnimation {
    const DURATION_MS: u32 = 750;
    fn is_active(&self) -> bool {
        if animation_disabled() {
            return false;
        }

        self.timer.is_running_within(self.duration)
    }

    fn eval(&self) -> f32 {
        if animation_disabled() {
            return 1.0;
        }

        self.timer.elapsed().to_millis() as f32 / 1000.0
    }

    fn opacity(&self, t: f32, pos_x: usize, pos_y: usize) -> u8 {
        if animation_disabled() {
            return 255;
        }

        let diag = pos_x + pos_y;

        let start = diag as f32 * 0.05;

        let f = pareen::constant(0.0)
            .seq_ease_in_out(
                start,
                easer::functions::Cubic,
                0.1,
                pareen::constant(1.0).eval(self.eval()),
            )
            .eval(t);

        (f * 255.0) as u8
    }

    fn header_opacity(&self, t: f32) -> u8 {
        if animation_disabled() {
            return 255;
        }
        let f = pareen::constant(0.0)
            .seq_ease_in_out(
                0.65,
                easer::functions::Linear,
                0.1,
                pareen::constant(1.0).eval(self.eval()),
            )
            .eval(t);

        (f * 255.0) as u8
    }

    fn start(&mut self) {
        self.active = true;
        self.timer.start();
    }

    fn reset(&mut self) {
        self.active = false;
        self.timer = Stopwatch::new_stopped();
    }

    fn lazy_start(&mut self, ctx: &mut EventCtx, event: Event) {
        if let Event::Attach(_) = event {
            if let Event::Attach(AttachType::Swipe(SwipeDirection::Up))
            | Event::Attach(AttachType::Swipe(SwipeDirection::Down))
            | Event::Attach(AttachType::Initial) = event
            {
                self.attach_top = true;
                self.duration = Duration::from_millis(Self::DURATION_MS);
            } else {
                self.duration = Duration::from_millis(Self::DURATION_MS);
            }
            self.reset();
            ctx.request_anim_frame();
        }
        if let Event::Timer(EventCtx::ANIM_FRAME_TIMER) = event {
            if !self.timer.is_running() {
                self.start();
            }
            if self.is_active() {
                ctx.request_anim_frame();
                ctx.request_paint();
            } else if self.active {
                self.active = false;
                ctx.request_anim_frame();
                ctx.request_paint();
            }
        }
    }
}

#[derive(Default, Clone)]
struct CloseAnimation {
    pub attach_top: bool,
    pub timer: Stopwatch,
    pub duration: Duration,
}
impl CloseAnimation {
    const DURATION_MS: u32 = 350;
    fn is_active(&self) -> bool {
        if animation_disabled() {
            return false;
        }

        self.timer.is_running_within(self.duration)
    }

    fn is_finished(&self) -> bool {
        if animation_disabled() {
            return true;
        }

        self.timer.is_running() && !self.timer.is_running_within(self.duration)
    }

    fn eval(&self) -> f32 {
        if animation_disabled() {
            return 1.0;
        }

        self.timer.elapsed().to_millis() as f32 / 1000.0
    }

    fn opacity(&self, t: f32, pos_x: usize, pos_y: usize) -> u8 {
        if animation_disabled() {
            return 255;
        }

        let diag = pos_x + pos_y;

        let start = diag as f32 * 0.05;

        let f = pareen::constant(1.0)
            .seq_ease_in_out(
                start,
                easer::functions::Cubic,
                0.1,
                pareen::constant(0.0).eval(self.eval()),
            )
            .eval(t);

        (f * 255.0) as u8
    }

    fn header_opacity(&self, t: f32) -> u8 {
        if animation_disabled() {
            return 255;
        }
        let f = pareen::constant(1.0)
            .seq_ease_in_out(
                0.10,
                easer::functions::Linear,
                0.25,
                pareen::constant(0.0).eval(self.eval()),
            )
            .eval(t);

        (f * 255.0) as u8
    }

    fn reset(&mut self) {
        self.timer = Stopwatch::new_stopped();
    }

    fn start(&mut self, ctx: &mut EventCtx) {
        self.duration = Duration::from_millis(Self::DURATION_MS);
        self.reset();
        self.timer.start();
        ctx.request_anim_frame();
        ctx.request_paint();
    }
    fn process(&mut self, ctx: &mut EventCtx, event: Event) {
        if let Event::Timer(EventCtx::ANIM_FRAME_TIMER) = event {
            if self.is_active() && !self.is_finished() {
                ctx.request_anim_frame();
                ctx.request_paint();
            }
        }
    }
}

pub struct PinKeyboard<'a> {
    allow_cancel: bool,
    show_erase: bool,
    show_cancel: bool,
    major_prompt: Label<'a>,
    minor_prompt: Label<'a>,
    major_warning: Option<Label<'a>>,
    keypad_area: Rect,
    textbox_area: Rect,
    textbox: PinDots,
    erase_btn: Button,
    cancel_btn: Button,
    confirm_btn: Button,
    digit_btns: [(Button, usize); DIGIT_COUNT],
    warning_timer: Option<TimerToken>,
    attach_animation: AttachAnimation,
    close_animation: CloseAnimation,
    close_confirm: bool,
}

impl<'a> PinKeyboard<'a> {
    pub fn new(
        major_prompt: TString<'a>,
        minor_prompt: TString<'a>,
        major_warning: Option<TString<'a>>,
        allow_cancel: bool,
    ) -> Self {
        // Control buttons.
        let erase_btn = Button::with_icon(theme::ICON_DELETE)
            .styled(theme::button_keyboard_erase())
            .with_long_press(theme::ERASE_HOLD_DURATION)
            .initially_enabled(false);

        let cancel_btn =
            Button::with_icon(theme::ICON_CLOSE).styled(theme::button_keyboard_cancel());

        Self {
            allow_cancel,
            show_erase: false,
            show_cancel: allow_cancel,
            major_prompt: Label::left_aligned(major_prompt, theme::label_keyboard()),
            minor_prompt: Label::right_aligned(minor_prompt, theme::label_keyboard_minor()),
            major_warning: major_warning
                .map(|text| Label::left_aligned(text, theme::label_keyboard_warning())),
            keypad_area: Rect::zero(),
            textbox_area: Rect::zero(),
            textbox: PinDots::new(theme::label_default()),
            erase_btn,
            cancel_btn,
            confirm_btn: Button::with_icon(theme::ICON_SIMPLE_CHECKMARK24)
                .styled(theme::button_pin_confirm())
                .initially_enabled(false),
            digit_btns: Self::generate_digit_buttons(),
            warning_timer: None,
            attach_animation: AttachAnimation::default(),
            close_animation: CloseAnimation::default(),
            close_confirm: false,
        }
    }

    fn generate_digit_buttons() -> [(Button, usize); DIGIT_COUNT] {
        // Generate a random sequence of digits from 0 to 9.
        let mut digits = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"];
        random::shuffle(&mut digits);
        digits
            .map(|c| Button::with_text(c.into()))
            .map(|b| {
                b.styled(theme::button_keyboard())
                    .with_text_align(Alignment::Center)
            })
            .map(|b| (b, 0))
    }

    fn pin_modified(&mut self, ctx: &mut EventCtx) {
        let is_full = self.textbox.is_full();
        let is_empty = self.textbox.is_empty();

        self.textbox.request_complete_repaint(ctx);

        if is_empty {
            self.major_prompt.request_complete_repaint(ctx);
            self.minor_prompt.request_complete_repaint(ctx);
            self.major_warning.request_complete_repaint(ctx);
        }

        let cancel_enabled = is_empty && self.allow_cancel;
        for btn in &mut self.digit_btns {
            btn.0.enable_if(ctx, !is_full);
        }

        self.show_erase = !is_empty;
        self.show_cancel = cancel_enabled && is_empty;

        self.erase_btn.enable_if(ctx, !is_empty);
        self.cancel_btn.enable_if(ctx, is_empty);
        self.confirm_btn.enable_if(ctx, !is_empty);
    }

    pub fn pin(&self) -> &str {
        self.textbox.pin()
    }

    fn get_button_alpha(&self, x: usize, y: usize, attach_time: f32, close_time: f32) -> u8 {
        self.attach_animation
            .opacity(attach_time, x, y)
            .min(self.close_animation.opacity(close_time, x, y))
    }

    fn get_textbox_alpha(&self, attach_time: f32, close_time: f32) -> u8 {
        self.attach_animation
            .header_opacity(attach_time)
            .min(self.close_animation.header_opacity(close_time))
    }
}

impl Component for PinKeyboard<'_> {
    type Msg = PinKeyboardMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        // Prompts and PIN dots display.
        let (header, keypad) =
            bounds.split_bottom(4 * theme::PIN_BUTTON_HEIGHT + 3 * theme::BUTTON_SPACING);
        let prompt = header.inset(HEADER_PADDING);

        // Keypad area.
        self.keypad_area = keypad;

        // Control buttons.
        let grid = Grid::new(keypad, 4, 3).with_spacing(theme::BUTTON_SPACING);

        // Prompts and PIN dots display.
        self.textbox_area = header;
        self.textbox.place(header);
        self.major_prompt.place(prompt);
        self.minor_prompt.place(prompt);
        self.major_warning.as_mut().map(|c| c.place(prompt));

        // Control buttons.
        let erase_cancel_area = grid.row_col(3, 0);
        self.erase_btn.place(erase_cancel_area);
        self.cancel_btn.place(erase_cancel_area);
        self.confirm_btn.place(grid.row_col(3, 2));

        // Digit buttons.
        for (i, btn) in self.digit_btns.iter_mut().enumerate() {
            // Assign the digits to buttons on a 4x3 grid, starting from the first row.
            let idx = if i < 9 {
                i
            } else {
                // For the last key (the "0" position) we skip one cell.
                i + 1
            };
            let area = grid.cell(idx);
            btn.0.place(area);
            btn.1 = idx;
        }

        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        self.close_animation.process(ctx, event);
        if self.close_animation.is_finished() && !animation_disabled() {
            return Some(if self.close_confirm {
                PinKeyboardMsg::Confirmed
            } else {
                PinKeyboardMsg::Cancelled
            });
        }

        self.attach_animation.lazy_start(ctx, event);

        match event {
            // Set up timer to switch off warning prompt.
            Event::Attach(_) if self.major_warning.is_some() => {
                self.warning_timer = Some(ctx.request_timer(Duration::from_secs(2)));
            }
            // Hide warning, show major prompt.
            Event::Timer(token) if Some(token) == self.warning_timer => {
                self.major_warning = None;
                self.minor_prompt.request_complete_repaint(ctx);
                ctx.request_paint();
            }
            _ => {}
        }

        // do not process buttons when closing
        if self.close_animation.is_active() {
            return None;
        }

        self.textbox.event(ctx, event);
        if let Some(Clicked) = self.confirm_btn.event(ctx, event) {
            if animation_disabled() {
                return Some(PinKeyboardMsg::Confirmed);
            } else {
                self.close_animation.start(ctx);
                self.close_confirm = true;
            }
        }
        if let Some(Clicked) = self.cancel_btn.event(ctx, event) {
            if animation_disabled() {
                return Some(PinKeyboardMsg::Cancelled);
            } else {
                self.close_animation.start(ctx);
                self.close_confirm = false;
            }
        }
        match self.erase_btn.event(ctx, event) {
            Some(ButtonMsg::Clicked) => {
                self.textbox.pop(ctx);
                self.pin_modified(ctx);
                return None;
            }
            Some(ButtonMsg::LongPressed) => {
                self.textbox.clear(ctx);
                self.pin_modified(ctx);
                return None;
            }
            _ => {}
        }
        for btn in &mut self.digit_btns {
            if let Some(Clicked) = btn.0.event(ctx, event) {
                if let ButtonContent::Text(text) = btn.0.content() {
                    text.map(|text| {
                        self.textbox.push(ctx, text);
                    });
                    self.pin_modified(ctx);
                    return None;
                }
            }
        }
        None
    }

    fn paint(&mut self) {
        todo!("remove when ui-t3t1 done");
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        let t_attach = self.attach_animation.eval();
        let t_close = self.close_animation.eval();

        let erase_alpha = self.get_button_alpha(0, 3, t_attach, t_close);

        if self.show_erase {
            self.erase_btn.render_with_alpha(target, erase_alpha);
        }

        if self.textbox.is_empty() {
            if let Some(ref w) = self.major_warning {
                w.render(target);
            } else {
                self.major_prompt.render(target);
            }
            self.minor_prompt.render(target);
            if self.show_cancel {
                self.cancel_btn.render_with_alpha(target, erase_alpha);
            }
        } else {
            self.textbox.render(target);
        }

        shape::Bar::new(self.textbox_area)
            .with_bg(theme::label_default().background_color)
            .with_fg(theme::label_default().background_color)
            .with_alpha(255 - self.get_textbox_alpha(t_attach, t_close))
            .render(target);

        let alpha = self.get_button_alpha(2, 3, t_attach, t_close);
        self.confirm_btn.render_with_alpha(target, alpha);

        for btn in &self.digit_btns {
            let alpha = self.get_button_alpha(btn.1 % 3, btn.1 / 3, t_attach, t_close);
            btn.0.render_with_alpha(target, alpha);
        }

        cshape::KeyboardOverlay::new(self.keypad_area).render(target);
    }
}

struct PinDots {
    area: Rect,
    pad: Pad,
    style: TextStyle,
    digits: ShortString,
    display_digits: bool,
}

impl PinDots {
    const DOT: i16 = 6;
    const PADDING: i16 = 7;
    const TWITCH: i16 = 4;

    fn new(style: TextStyle) -> Self {
        Self {
            area: Rect::zero(),
            pad: Pad::with_background(style.background_color),
            style,
            digits: ShortString::new(),
            display_digits: false,
        }
    }

    fn size(&self) -> Offset {
        let ndots = self.digits.len().min(MAX_VISIBLE_DOTS);
        let mut width = Self::DOT * (ndots as i16);
        width += Self::PADDING * (ndots.saturating_sub(1) as i16);
        Offset::new(width, Self::DOT)
    }

    fn is_empty(&self) -> bool {
        self.digits.is_empty()
    }

    fn is_full(&self) -> bool {
        self.digits.len() >= MAX_LENGTH
    }

    fn clear(&mut self, ctx: &mut EventCtx) {
        self.digits.clear();
        ctx.request_paint()
    }

    fn push(&mut self, ctx: &mut EventCtx, text: &str) {
        if self.digits.push_str(text).is_err() {
            // `self.pin` is full and wasn't able to accept all of
            // `text`. Should not happen.
        };
        ctx.request_paint()
    }

    fn pop(&mut self, ctx: &mut EventCtx) {
        if self.digits.pop().is_some() {
            ctx.request_paint()
        }
    }

    fn pin(&self) -> &str {
        &self.digits
    }

    fn render_digits<'s>(&self, area: Rect, target: &mut impl Renderer<'s>) {
        let left = area.left_center() + Offset::y(Font::MONO.visible_text_height("1") / 2);
        let digits = self.digits.len();

        if digits <= MAX_VISIBLE_DIGITS {
            shape::Text::new(left, &self.digits)
                .with_align(Alignment::Start)
                .with_font(Font::MONO)
                .with_fg(self.style.text_color)
                .render(target);
        } else {
            let offset: usize = digits.saturating_sub(MAX_VISIBLE_DIGITS);
            shape::Text::new(left, &self.digits[offset..])
                .with_align(Alignment::Start)
                .with_font(Font::MONO)
                .with_fg(self.style.text_color)
                .render(target);
        }
    }

    fn render_dots<'s>(&self, area: Rect, target: &mut impl Renderer<'s>) {
        let mut cursor = area.left_center();

        let digits = self.digits.len();
        let dots_visible = digits.min(MAX_VISIBLE_DOTS);
        let step = Self::DOT + Self::PADDING;

        // Jiggle when overflowed.
        if digits > MAX_VISIBLE_DOTS + 1 && (digits + 1) % 2 == 0 {
            cursor.x += Self::TWITCH
        }

        let mut digit_idx = 0;
        // Small leftmost dot.
        if digits > MAX_VISIBLE_DOTS + 1 {
            shape::ToifImage::new(cursor, theme::DOT_SMALL.toif)
                .with_align(Alignment2D::CENTER_LEFT)
                .with_fg(theme::GREY)
                .render(target);
            cursor.x += step;
            digit_idx += 1;
        }

        // Greyed out dot.
        if digits > MAX_VISIBLE_DOTS {
            shape::ToifImage::new(cursor, theme::DOT_SMALL.toif)
                .with_align(Alignment2D::CENTER_LEFT)
                .with_fg(self.style.text_color)
                .render(target);
            cursor.x += step;
            digit_idx += 1;
        }

        // Draw a dot for each PIN digit.
        for _ in digit_idx..dots_visible {
            shape::ToifImage::new(cursor, theme::ICON_PIN_BULLET.toif)
                .with_align(Alignment2D::CENTER_LEFT)
                .with_fg(self.style.text_color)
                .render(target);
            cursor.x += step;
        }
    }
}

impl Component for PinDots {
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.pad.place(bounds);
        self.area = bounds;
        self.area
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        match event {
            Event::Touch(TouchEvent::TouchStart(pos)) => {
                if self.area.contains(pos) {
                    self.display_digits = true;
                    self.pad.clear();
                    ctx.request_paint();
                };
                None
            }
            Event::Touch(TouchEvent::TouchEnd(_)) => {
                if mem::replace(&mut self.display_digits, false) {
                    self.pad.clear();
                    ctx.request_paint();
                };
                None
            }
            _ => None,
        }
    }

    fn paint(&mut self) {
        // TODO: remove when ui-t3t1 done
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        let dot_area = self.area.inset(HEADER_PADDING);
        self.pad.render(target);
        if self.display_digits {
            self.render_digits(dot_area, target)
        } else {
            self.render_dots(dot_area, target)
        }
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for PinKeyboard<'_> {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("PinKeyboard");
        // So that debuglink knows the locations of the buttons
        let mut digits_order = ShortString::new();
        for btn in self.digit_btns.iter() {
            let btn_content = btn.0.content();
            if let ButtonContent::Text(text) = btn_content {
                text.map(|text| {
                    unwrap!(digits_order.push_str(text));
                });
            }
        }
        t.string("digits_order", digits_order.as_str().into());
        t.string("pin", self.textbox.pin().into());
        t.bool("display_digits", self.textbox.display_digits);
    }
}
