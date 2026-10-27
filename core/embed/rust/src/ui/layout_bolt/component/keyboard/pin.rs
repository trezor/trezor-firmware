use core::mem;

use sys::time::{Duration, Instant};

use super::super::super::fonts;
use super::super::button::ButtonMsg::{self, Clicked};
use super::super::button::{Button, ButtonContent};
use super::super::theme;
use crate::strutil::{ShortString, TString};
use crate::trezorhal::random;
use crate::ui::component::base::ComponentExt;
use crate::ui::component::text::TextStyle;
use crate::ui::component::{Child, Component, Event, EventCtx, Marquee, Maybe, Never, Pad, Timer};
use crate::ui::display::Font;
use crate::ui::event::TouchEvent;
use crate::ui::geometry::{Alignment, Alignment2D, Grid, Insets, Offset, Point, Rect};
use crate::ui::shape::{Renderer, Text, ToifImage};
use crate::ui::util::DisplayStyle;

#[cfg_attr(feature = "debug", derive(ufmt::derive::uDebug))]
pub enum PinKeyboardMsg {
    Confirmed,
    Cancelled,
}

const MAX_LENGTH: usize = 50;
const MAX_SHOWN_LEN: usize = 16;
const DIGIT_COUNT: usize = 10; // 0..10

const HEADER_PADDING_SIDE: i16 = 5;
const HEADER_PADDING_BOTTOM: i16 = 12;

const HEADER_PADDING: Insets = Insets::new(
    theme::borders().top,
    HEADER_PADDING_SIDE,
    HEADER_PADDING_BOTTOM,
    HEADER_PADDING_SIDE,
);

const LAST_DIGIT_TIMEOUT: Duration = Duration::from_secs(1);

pub struct PinKeyboard {
    allow_cancel: bool,
    major_prompt: Marquee,
    minor_prompt: Marquee,
    major_warning: Option<Marquee>,
    textbox: Child<PinInput>,
    textbox_pad: Pad,
    erase_btn: Child<Maybe<Button>>,
    cancel_btn: Child<Maybe<Button>>,
    confirm_btn: Child<Button>,
    digit_btns: [Child<Button>; DIGIT_COUNT],
    warning_timer: Timer,
}

impl PinKeyboard {
    // Label position fine-tuning.
    const MAJOR_OFF: Offset = Offset::y(11);
    const MINOR_OFF: Offset = Offset::y(11);

    pub fn new(
        major_prompt: TString<'static>,
        minor_prompt: TString<'static>,
        major_warning: Option<TString<'static>>,
        allow_cancel: bool,
    ) -> Self {
        // Control buttons.
        let erase_btn = Button::with_icon_blend(
            theme::IMAGE_BG_BACK_BTN,
            theme::ICON_BACK,
            Offset::new(30, 12),
        )
        .styled(theme::button_reset())
        .with_long_press(theme::ERASE_HOLD_DURATION)
        .initially_enabled(false);
        let erase_btn = Maybe::hidden(theme::BG, erase_btn).into_child();

        let cancel_btn = Button::with_icon(theme::ICON_CANCEL).styled(theme::button_cancel());
        let cancel_btn = Maybe::new(theme::BG, cancel_btn, allow_cancel).into_child();

        Self {
            allow_cancel,
            major_prompt: Self::prompt_marquee(major_prompt, theme::label_keyboard()),
            minor_prompt: Self::prompt_marquee(minor_prompt, theme::label_keyboard_minor())
                .with_alignment(Alignment::End),
            major_warning: major_warning
                .map(|text| Self::prompt_marquee(text, theme::label_keyboard_warning())),
            textbox: PinInput::new(theme::label_default()).into_child(),
            textbox_pad: Pad::with_background(theme::label_default().background_color),
            erase_btn,
            cancel_btn,
            confirm_btn: Button::with_icon(theme::ICON_CONFIRM)
                .styled(theme::button_confirm())
                .initially_enabled(false)
                .into_child(),
            digit_btns: Self::generate_digit_buttons(),
            warning_timer: Timer::new(),
        }
    }

    fn generate_digit_buttons() -> [Child<Button>; DIGIT_COUNT] {
        // Generate a random sequence of digits from 0 to 9.
        let mut digits = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"];
        random::shuffle(&mut digits);
        digits
            .map(|c| Button::with_text(c.into()))
            .map(|b| b.styled(theme::button_pin()))
            .map(Child::new)
    }

    fn pin_modified(&mut self, ctx: &mut EventCtx) {
        let is_full = self.textbox.inner().is_full();
        let is_empty = self.textbox.inner().is_empty();

        self.textbox_pad.clear();
        self.textbox.request_complete_repaint(ctx);

        if is_empty {
            self.restart_prompts(ctx);
            self.major_prompt.request_complete_repaint(ctx);
            self.minor_prompt.request_complete_repaint(ctx);
            self.major_warning.request_complete_repaint(ctx);
        }

        let cancel_enabled = is_empty && self.allow_cancel;
        for btn in &mut self.digit_btns {
            btn.mutate(ctx, |ctx, btn| btn.enable_if(ctx, !is_full));
        }
        self.erase_btn.mutate(ctx, |ctx, btn| {
            btn.show_if(ctx, !is_empty);
            btn.inner_mut().enable_if(ctx, !is_empty);
        });
        self.cancel_btn.mutate(ctx, |ctx, btn| {
            btn.show_if(ctx, cancel_enabled);
            btn.inner_mut().enable_if(ctx, is_empty);
        });
        self.confirm_btn
            .mutate(ctx, |ctx, btn| btn.enable_if(ctx, !is_empty));
    }

    /// Scroll the visible prompts from the beginning. The prompts are visible
    /// only while the PIN is empty, the warning (if any) replacing the major
    /// prompt. Their marquees are driven only while visible, so this is to be
    /// called whenever the visible prompts change.
    fn restart_prompts(&mut self, ctx: &mut EventCtx) {
        if !self.textbox.inner().is_empty() {
            return;
        }
        let now = Instant::now();
        let major = match &mut self.major_warning {
            Some(w) => w,
            None => &mut self.major_prompt,
        };
        for marquee in [major, &mut self.minor_prompt] {
            marquee.reset();
            marquee.start(ctx, now);
        }
    }

    pub fn pin(&self) -> &str {
        self.textbox.inner().pin()
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
    fn prompt_marquee_area(strip: Rect, font: Font) -> Rect {
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
}

impl Component for PinKeyboard {
    type Msg = PinKeyboardMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        // Ignore the top padding for now, we need it to reliably register textbox touch
        // events.
        let borders_no_top = Insets {
            top: 0,
            ..theme::borders()
        };
        // Prompts and PIN dots display.
        let (header, keypad) = bounds
            .inset(borders_no_top)
            .split_bottom(4 * theme::PIN_BUTTON_HEIGHT + 3 * theme::BUTTON_SPACING);
        let prompt = header.inset(HEADER_PADDING);
        // The minor prompt takes exactly the width it needs; the major prompt
        // (and the warning temporarily replacing it) takes the rest and
        // scrolls if it does not fit.
        let minor_width = self.minor_prompt_width().min(prompt.width());
        let (major_area, minor_area) = prompt.split_right(minor_width);
        let major_area = major_area.translate(Self::MAJOR_OFF);
        let minor_area = minor_area.translate(Self::MINOR_OFF);
        let major_font = theme::label_keyboard().text_font;
        let minor_font = theme::label_keyboard_minor().text_font;

        // Control buttons.
        let grid = Grid::new(keypad, 4, 3).with_spacing(theme::BUTTON_SPACING);

        // Prompts and PIN dots display.
        self.textbox_pad.place(header);
        self.textbox.place(header);
        self.major_prompt
            .place(Self::prompt_marquee_area(major_area, major_font));
        self.minor_prompt
            .place(Self::prompt_marquee_area(minor_area, minor_font));
        self.major_warning
            .place(Self::prompt_marquee_area(major_area, major_font));

        // Control buttons.
        let erase_cancel_area = grid.row_col(3, 0);
        self.erase_btn.place(erase_cancel_area);
        self.cancel_btn.place(erase_cancel_area);
        self.confirm_btn.place(grid.row_col(3, 2));

        // Digit buttons.
        for (i, btn) in self.digit_btns.iter_mut().enumerate() {
            // Assign the digits to buttons on a 4x3 grid, starting from the first row.
            let area = grid.cell(if i < 9 {
                i
            } else {
                // For the last key (the "0" position) we skip one cell.
                i + 1
            });
            btn.place(area);
        }

        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        // Drive only the visible prompt marquees (see `restart_prompts`).
        if self.textbox.inner().is_empty() {
            match &mut self.major_warning {
                Some(w) => w.event(ctx, event),
                None => self.major_prompt.event(ctx, event),
            };
            self.minor_prompt.event(ctx, event);
        }

        match event {
            Event::Attach(_) => {
                self.restart_prompts(ctx);
                // Set up timer to switch off warning prompt.
                if self.major_warning.is_some() {
                    self.warning_timer.start(ctx, Duration::from_secs(2));
                }
            }
            // Hide warning, show major prompt.
            Event::Timer(_) if self.warning_timer.expire(event) => {
                self.major_warning = None;
                self.restart_prompts(ctx);
                self.textbox_pad.clear();
                self.minor_prompt.request_complete_repaint(ctx);
                ctx.request_paint();
            }
            _ => {}
        }

        self.textbox.event(ctx, event);
        if let Some(Clicked) = self.confirm_btn.event(ctx, event) {
            return Some(PinKeyboardMsg::Confirmed);
        }
        if let Some(Clicked) = self.cancel_btn.event(ctx, event) {
            return Some(PinKeyboardMsg::Cancelled);
        }
        match self.erase_btn.event(ctx, event) {
            Some(ButtonMsg::Clicked) => {
                self.textbox.mutate(ctx, |ctx, t| t.pop(ctx));
                self.pin_modified(ctx);
                return None;
            }
            Some(ButtonMsg::LongPressed) => {
                self.textbox.mutate(ctx, |ctx, t| t.clear(ctx));
                self.pin_modified(ctx);
                return None;
            }
            _ => {}
        }
        for btn in &mut self.digit_btns {
            if let Some(Clicked) = btn.event(ctx, event) {
                if let ButtonContent::Text(text) = btn.inner().content() {
                    text.map(|text| {
                        self.textbox.mutate(ctx, |ctx, t| t.push(ctx, text));
                    });
                    self.pin_modified(ctx);
                    self.textbox.mutate(ctx, |ctx, t| {
                        t.last_digit_timer.start(ctx, LAST_DIGIT_TIMEOUT);
                        t.display_style = DisplayStyle::LastOnly;
                    });
                    self.textbox.request_complete_repaint(ctx);
                    ctx.request_paint();
                    return None;
                }
            }
        }
        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.erase_btn.render(target);
        self.textbox_pad.render(target);
        if self.textbox.inner().is_empty() {
            if let Some(ref w) = self.major_warning {
                w.render(target);
            } else {
                self.major_prompt.render(target);
            }
            self.minor_prompt.render(target);
            self.cancel_btn.render(target);
        } else {
            self.textbox.render(target);
        }
        self.confirm_btn.render(target);
        for btn in &self.digit_btns {
            btn.render(target);
        }
    }
}

struct PinInput {
    area: Rect,
    pad: Pad,
    style: TextStyle,
    digits: ShortString,
    last_digit_timer: Timer,
    display_style: DisplayStyle,
}

impl PinInput {
    const ICON_WIDTH: i16 = 6;
    const ICON_SPACING: i16 = 6;
    const TWITCH: i16 = 4;

    fn new(style: TextStyle) -> Self {
        let digits = ShortString::new();
        debug_assert!(digits.capacity() >= MAX_LENGTH);
        Self {
            area: Rect::zero(),
            pad: Pad::with_background(style.background_color),
            style,
            digits,
            last_digit_timer: Timer::new(),
            display_style: DisplayStyle::Hidden,
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

        let center = area.center() + Offset::y(fonts::FONT_MONO.text_height() / 2);
        let right =
            center + Offset::x(fonts::FONT_MONO.text_width("0") * (MAX_SHOWN_LEN as i16) / 2);
        let pin_len = self.digits.len();

        if pin_len <= MAX_SHOWN_LEN {
            Text::new(center, &self.digits, fonts::FONT_MONO)
                .with_align(Alignment::Center)
                .with_fg(self.style.text_color)
                .render(target);
        } else {
            let offset = pin_len.saturating_sub(MAX_SHOWN_LEN);
            Text::new(right, &self.digits[offset..], fonts::FONT_MONO)
                .with_align(Alignment::End)
                .with_fg(self.style.text_color)
                .render(target);
        }
    }

    fn render_hidden<'s>(&self, area: Rect, target: &mut impl Renderer<'s>) {
        debug_assert_ne!(self.display_style, DisplayStyle::Shown);

        let mut cursor = self.size().snap(area.center(), Alignment2D::CENTER);

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
                .with_align(Alignment2D::TOP_LEFT)
                .with_fg(self.style.text_color)
                .render(target);
            cursor.x += step;
            char_idx += 1;
        }

        // Greyed out dot.
        if pin_len > MAX_SHOWN_LEN {
            ToifImage::new(cursor, theme::DOT_ACTIVE.toif)
                .with_align(Alignment2D::TOP_LEFT)
                .with_fg(theme::GREY_LIGHT)
                .render(target);
            cursor.x += step;
            char_idx += 1;
        }

        if visible_icons > 0 {
            // Classical icons
            for _ in char_idx..visible_icons {
                ToifImage::new(cursor, theme::DOT_ACTIVE.toif)
                    .with_align(Alignment2D::TOP_LEFT)
                    .with_fg(self.style.text_color)
                    .render(target);
                cursor.x += step;
            }
        }

        if last_digit {
            // This should not fail because pin_len > 0
            let last = &self.digits.as_str()[(pin_len - 1)..pin_len];

            // Adapt x and y positions for the character
            cursor.y = area.center().y + (fonts::FONT_MONO.text_height() / 2);
            cursor.x += Self::ICON_WIDTH / 2;

            // Paint the last character
            Text::new(cursor, last, fonts::FONT_MONO)
                .with_align(Alignment::Center)
                .with_fg(self.style.text_color)
                .render(target);
        }
    }
}

impl Component for PinInput {
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
                // Show the entire pin on the touch start
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
            let btn_content = btn.inner().content();

            if let ButtonContent::Text(text) = btn_content {
                text.map(|text| {
                    unwrap!(digits_order.push_str(text));
                });
            }
        }
        let display_style = uformat!("{:?}", self.textbox.inner().display_style);
        t.string("digits_order", digits_order.as_str().into());
        t.string("pin", self.textbox.inner().pin().into());
        t.string("display_style", display_style.as_str().into());
    }
}
