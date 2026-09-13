use core::mem;

use sys::time::{Duration, Instant};

use super::super::super::component::button::ButtonMsg::{self, Clicked};
use super::super::super::component::button::{Button, ButtonContent};
use super::super::super::component::theme;
use super::super::super::cshape;
use super::super::super::fonts::FONT_MONO;
use crate::strutil::{ShortString, TString};
use crate::time::Stopwatch;
use crate::trezorhal::random;
use crate::ui::component::base::{AttachType, ComponentExt};
use crate::ui::component::text::TextStyle;
use crate::ui::component::{Component, Event, EventCtx, Marquee, Never, Pad, Timer};
use crate::ui::event::TouchEvent;
use crate::ui::geometry::{Alignment, Alignment2D, Direction, Grid, Insets, Offset, Point, Rect};
use crate::ui::shape::{Bar, Renderer, Text, ToifImage};
use crate::ui::util::{animation_disabled, DisplayStyle};

pub enum PinKeyboardMsg {
    Confirmed,
    Cancelled,
}

const MAX_LENGTH: usize = 50;
const MAX_SHOWN_LEN: usize = 18;
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

const LAST_DIGIT_TIMEOUT: Duration = Duration::from_secs(1);

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
            if let Event::Attach(AttachType::Swipe(Direction::Up))
            | Event::Attach(AttachType::Swipe(Direction::Down))
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

pub struct PinKeyboard {
    allow_cancel: bool,
    show_erase: bool,
    show_cancel: bool,
    major_prompt: Marquee,
    minor_prompt: Marquee,
    major_warning: Option<Marquee>,
    keypad_area: Rect,
    textbox_area: Rect,
    textbox: PinDots,
    erase_btn: Button,
    cancel_btn: Button,
    confirm_btn: Button,
    digit_btns: [(Button, usize); DIGIT_COUNT],
    warning_timer: Timer,
    attach_animation: AttachAnimation,
    close_animation: CloseAnimation,
    close_confirm: bool,
}

impl PinKeyboard {
    pub fn new(
        major_prompt: TString<'static>,
        minor_prompt: TString<'static>,
        major_warning: Option<TString<'static>>,
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
            major_prompt: Self::prompt_marquee(major_prompt, theme::label_keyboard()),
            minor_prompt: Self::prompt_marquee(minor_prompt, theme::label_keyboard_minor())
                .with_alignment(Alignment::End),
            major_warning: major_warning
                .map(|text| Self::prompt_marquee(text, theme::label_keyboard_warning())),
            keypad_area: Rect::zero(),
            textbox_area: Rect::zero(),
            textbox: PinDots::new(theme::label_default()),
            erase_btn,
            cancel_btn,
            confirm_btn: Button::with_icon(theme::ICON_SIMPLE_CHECKMARK24)
                .styled(theme::button_pin_confirm())
                .initially_enabled(false),
            digit_btns: Self::generate_digit_buttons(),
            warning_timer: Timer::new(),
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
            // The prompts become visible again; reset and restart the visible
            // marquees so they scroll from the beginning.
            if self.major_warning.is_none() {
                self.major_prompt.reset();
                self.major_prompt.start(ctx, Instant::now());
            }
            self.minor_prompt.reset();
            self.minor_prompt.start(ctx, Instant::now());
            if let Some(w) = &mut self.major_warning {
                w.reset();
                w.start(ctx, Instant::now());
            }
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

    fn prompt_marquee(text: TString<'static>, style: TextStyle) -> Marquee {
        Marquee::new(
            text,
            style.text_font,
            style.text_color,
            style.background_color,
        )
    }

    /// Area of a `Marquee` replacing a top-aligned `Label` in `strip`:
    /// `Marquee` renders the text baseline at `text_height - 1` below the top
    /// of its area while `Label` places it at `text_max_height -
    /// text_baseline`, so the area is shifted to make the baselines match.
    /// The bottom of the area covers the descent so that descenders are not
    /// clipped.
    fn prompt_marquee_area(strip: Rect) -> Rect {
        let font = theme::label_keyboard().text_font;
        let baseline_y = strip.y0 + font.text_max_height() - font.text_baseline();
        let top = baseline_y - (font.text_height() - 1);
        Rect::from_top_left_and_size(
            Point::new(strip.x0, top),
            Offset::new(strip.width(), baseline_y + font.text_baseline() - top),
        )
    }

    /// Width needed by the minor prompt, which always gets exactly as much
    /// space as it needs (so it never scrolls); the major prompt takes the
    /// rest and scrolls if it does not fit.
    fn minor_prompt_width(&self) -> i16 {
        let font = theme::label_keyboard_minor().text_font;
        self.minor_prompt.text().map(|t| font.text_width(t))
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

impl Component for PinKeyboard {
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
        // The minor prompt takes exactly the width it needs; the major prompt
        // (and the warning temporarily replacing it) takes the rest and
        // scrolls if it does not fit.
        let minor_width = self.minor_prompt_width().min(prompt.width());
        let (major_area, minor_area) = prompt.split_right(minor_width);
        self.major_prompt
            .place(Self::prompt_marquee_area(major_area));
        self.minor_prompt
            .place(Self::prompt_marquee_area(minor_area));
        self.major_warning
            .as_mut()
            .map(|c| c.place(Self::prompt_marquee_area(major_area)));

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

        // Start and drive the prompt marquees only while they are visible,
        // i.e. while the PIN textbox is empty (matching render). While the
        // warning is visible, it replaces the major prompt, which is neither
        // started nor advanced until the warning expires.
        if self.textbox.is_empty() {
            if let Event::Attach(_) = event {
                if self.major_warning.is_none() {
                    self.major_prompt.start(ctx, Instant::now());
                }
                self.minor_prompt.start(ctx, Instant::now());
                if let Some(w) = &mut self.major_warning {
                    w.start(ctx, Instant::now());
                }
            } else if self.major_warning.is_some() {
                self.minor_prompt.event(ctx, event);
                if let Some(w) = &mut self.major_warning {
                    w.event(ctx, event);
                }
            } else {
                self.major_prompt.event(ctx, event);
                self.minor_prompt.event(ctx, event);
            }
        }

        match event {
            // Set up timer to switch off warning prompt.
            Event::Attach(_) if self.major_warning.is_some() => {
                self.warning_timer.start(ctx, Duration::from_secs(2));
            }
            // Hide warning, show major prompt from the beginning.
            Event::Timer(_) if self.warning_timer.expire(event) => {
                self.major_warning = None;
                self.major_prompt.reset();
                self.major_prompt.start(ctx, Instant::now());
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
                    self.textbox.last_digit_timer.start(ctx, LAST_DIGIT_TIMEOUT);
                    self.textbox.display_style = DisplayStyle::LastOnly;
                    self.textbox.request_complete_repaint(ctx);
                    ctx.request_paint();
                    return None;
                }
            }
        }
        None
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

        Bar::new(self.textbox_area)
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
    display_style: DisplayStyle,
    last_digit_timer: Timer,
}

impl PinDots {
    const ICON_WIDTH: i16 = 6;
    const ICON_SPACING: i16 = 7;
    const TWITCH: i16 = 4;

    fn new(style: TextStyle) -> Self {
        Self {
            area: Rect::zero(),
            pad: Pad::with_background(style.background_color),
            style,
            digits: ShortString::new(),
            display_style: DisplayStyle::Hidden,
            last_digit_timer: Timer::new(),
        }
    }

    fn size(&self) -> Offset {
        let ndots = self.digits.len().min(MAX_SHOWN_LEN);
        let mut width = Self::ICON_WIDTH * (ndots as i16);
        width += Self::ICON_SPACING * (ndots.saturating_sub(1) as i16);
        Offset::new(width, Self::ICON_WIDTH)
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

    fn render_shown<'s>(&self, area: Rect, target: &mut impl Renderer<'s>) {
        // Make sure the pin should be shown
        debug_assert_eq!(self.display_style, DisplayStyle::Shown);

        let left = area.left_center() + Offset::y(FONT_MONO.visible_text_height("1") / 2);
        let pin_len = self.digits.len();

        let offset = pin_len.saturating_sub(MAX_SHOWN_LEN);
        let visible_digits = if pin_len <= MAX_SHOWN_LEN {
            &self.digits
        } else {
            &self.digits[offset..]
        };

        Text::new(left, visible_digits, FONT_MONO)
            .with_align(Alignment::Start)
            .with_fg(self.style.text_color)
            .render(target);
    }

    fn render_hidden<'s>(&self, area: Rect, target: &mut impl Renderer<'s>) {
        debug_assert_ne!(self.display_style, DisplayStyle::Shown);

        let mut cursor = area.left_center();

        let pin_len = self.digits.len();
        let last_digit = self.display_style == DisplayStyle::LastOnly;
        let step = Self::ICON_WIDTH + Self::ICON_SPACING;

        // Render only when there are characters
        if pin_len == 0 {
            return;
        }

        // Number of visible icons + characters
        let visible_len = pin_len.min(MAX_SHOWN_LEN);
        // Number of visible icons
        let visible_icons = visible_len - usize::from(last_digit);

        // Jiggle when overflowed.
        if pin_len > visible_len && pin_len % 2 == 1 && self.display_style != DisplayStyle::Shown {
            cursor.x += Self::TWITCH;
        }

        let mut char_idx = 0;

        // Small leftmost dot.
        if pin_len > MAX_SHOWN_LEN + 1 {
            ToifImage::new(cursor, theme::DOT_SMALL.toif)
                .with_align(Alignment2D::CENTER_LEFT)
                .with_fg(theme::GREY)
                .render(target);
            cursor.x += step;
            char_idx += 1;
        }

        // Greyed out dot.
        if pin_len > MAX_SHOWN_LEN {
            ToifImage::new(cursor, theme::DOT_SMALL.toif)
                .with_align(Alignment2D::CENTER_LEFT)
                .with_fg(self.style.text_color)
                .render(target);
            cursor.x += step;
            char_idx += 1;
        }

        if visible_icons > 0 {
            // Classical icons
            for _ in char_idx..visible_icons {
                ToifImage::new(cursor, theme::ICON_PIN_BULLET.toif)
                    .with_align(Alignment2D::CENTER_LEFT)
                    .with_fg(self.style.text_color)
                    .render(target);
                cursor.x += step;
            }
        }

        if last_digit {
            // This should not fail because pin_len > 0
            let last = &self.digits.as_str()[(pin_len - 1)..pin_len];

            // Adapt x and y positions for the character
            cursor.y = area.left_center().y + (FONT_MONO.visible_text_height("1") / 2);

            // Paint the last character
            Text::new(cursor, last, FONT_MONO)
                .with_align(Alignment::Start)
                .with_fg(self.style.text_color)
                .render(target);
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
            Event::Touch(TouchEvent::TouchStart(pos)) if self.area.contains(pos) => {
                // Stop the last char timer
                self.last_digit_timer.stop();
                self.display_style = DisplayStyle::Shown;
                self.pad.clear();
                ctx.request_paint();
                None
            }
            Event::Touch(TouchEvent::TouchEnd(_)) => {
                if mem::replace(&mut self.display_style, DisplayStyle::Hidden)
                    == DisplayStyle::Shown
                {
                    self.pad.clear();
                    ctx.request_paint();
                };
                None
            }
            // Timeout for showing the last digit.
            Event::Timer(_) if self.last_digit_timer.expire(event) => {
                self.display_style = DisplayStyle::Hidden;
                self.request_complete_repaint(ctx);
                ctx.request_paint();
                None
            }
            _ => None,
        }
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        let pin_area = self.area.inset(HEADER_PADDING);
        self.pad.render(target);

        if !self.digits.is_empty() {
            match self.display_style {
                DisplayStyle::Shown => self.render_shown(pin_area, target),
                _ => self.render_hidden(pin_area, target),
            }
        }
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for PinKeyboard {
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
        let display_style = uformat!("{:?}", self.textbox.display_style);
        t.string("digits_order", digits_order.as_str().into());
        t.string("pin", self.textbox.pin().into());
        t.string("display_style", display_style.as_str().into());
    }
}
