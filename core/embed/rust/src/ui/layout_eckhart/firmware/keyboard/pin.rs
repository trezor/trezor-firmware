use crate::{
    strutil::{ShortString, TString},
    time::Duration,
    ui::{
        component::{
            text::{
                layout::{Chunks, LayoutFit},
                LineBreaking, TextStyle,
            },
            Component, Event, EventCtx, Label, TextLayout, Timer,
        },
        display::Icon,
        event::TouchEvent,
        geometry::{Alignment, Alignment2D, Insets, Offset, Rect},
        shape::{Bar, Renderer, Text, ToifImage},
        util::DisplayStyle,
    },
};

use super::{
    super::super::{component::ButtonContent, constant::SCREEN, theme},
    common::{
        FADING_ICON_COLORS, FADING_ICON_COUNT, INPUT_TOUCH_HEIGHT, KEYBOARD_INPUT_INSETS,
        KEYBOARD_INPUT_RADIUS, KEYBOARD_PROMPT_INSETS, KEYPAD_VISIBLE_HEIGHT, SHOWN_INSETS,
    },
    keypad::{ButtonState, Keypad, KeypadMsg, KeypadState},
};

pub enum PinKeyboardMsg {
    Confirmed,
    Cancelled,
}

pub struct PinKeyboard<'a> {
    prompt: Label<'a>,
    attempts: Label<'a>,
    warning: Option<Label<'a>>,
    allow_cancel: bool,
    last_attempt: bool,
    keypad: Keypad,
    input: PinInput,
    warning_timer: Timer,
}

impl<'a> PinKeyboard<'a> {
    const LAST_DIGIT_TIMEOUT: Duration = Duration::from_secs(1);
    const MAJOR_WARNING_TIMEOUT: Duration = Duration::from_secs(2);
    // Ad hoc number that so that all languages can reasonably show the attempts
    // prompt
    const ATTEMPTS_WIDTH: i16 = 85;

    pub fn new(
        prompt: TString<'a>,
        attempts: TString<'a>,
        warning: Option<TString<'a>>,
        allow_cancel: bool,
        last_attempt: bool,
    ) -> Self {
        let attempts_style = if last_attempt {
            theme::label_title_warning()
        } else {
            theme::TEXT_SMALL_LIGHT
        }
        .with_line_breaking(LineBreaking::BreakAtWhitespace);
        Self {
            prompt: Label::left_aligned(prompt, theme::firmware::TEXT_SMALL).vertically_centered(),
            attempts: Label::centered(attempts, attempts_style).vertically_centered(),
            warning: warning.map(|text| {
                Label::left_aligned(text, theme::firmware::TEXT_SMALL).vertically_centered()
            }),
            allow_cancel,
            last_attempt,
            input: PinInput::new(),
            keypad: Keypad::new_numeric(true),
            warning_timer: Timer::new(),
        }
    }

    fn update_keypad_state(&mut self, ctx: &mut EventCtx) {
        let keypad_state = match self.input.display_style {
            DisplayStyle::Shown => {
                // Disable the entire active keypad
                KeypadState {
                    back: ButtonState::Hidden,
                    erase: ButtonState::Disabled,
                    cancel: ButtonState::Hidden,
                    confirm: ButtonState::Disabled,
                    keys: ButtonState::Disabled,
                    override_key: None,
                }
            }
            _ => {
                if self.input.is_full() {
                    // Disable all except of confirm and erase buttons
                    KeypadState {
                        back: ButtonState::Hidden,
                        erase: ButtonState::Enabled,
                        cancel: ButtonState::Hidden,
                        confirm: ButtonState::Enabled,
                        keys: ButtonState::Disabled,
                        override_key: None,
                    }
                } else if self.input.is_empty() {
                    KeypadState {
                        back: ButtonState::Hidden,
                        erase: ButtonState::Hidden,
                        cancel: if self.allow_cancel {
                            ButtonState::Enabled
                        } else {
                            ButtonState::Hidden
                        },
                        confirm: ButtonState::Hidden,
                        keys: ButtonState::Enabled,
                        override_key: None,
                    }
                } else {
                    KeypadState {
                        back: ButtonState::Hidden,
                        erase: ButtonState::Enabled,
                        cancel: ButtonState::Hidden,
                        confirm: ButtonState::Enabled,
                        keys: ButtonState::Enabled,
                        override_key: None,
                    }
                }
            }
        };
        // Apply all button states
        self.keypad.set_state(keypad_state, ctx);
    }

    pub fn pin(&self) -> &str {
        self.input.pin()
    }
}

impl Component for PinKeyboard<'_> {
    type Msg = PinKeyboardMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        // assert full screen
        debug_assert_eq!(bounds.height(), SCREEN.height());
        debug_assert_eq!(bounds.width(), SCREEN.width());

        // Keypad and input areas are overlapped
        let (_, keypad_area) = bounds.split_bottom(KEYPAD_VISIBLE_HEIGHT);
        let (input_touch_area, _) = bounds.split_top(INPUT_TOUCH_HEIGHT);

        let prompts_area = input_touch_area.inset(KEYBOARD_PROMPT_INSETS);
        let (prompt_area, attempts_area) = prompts_area.split_right(Self::ATTEMPTS_WIDTH);

        // Prompts and PIN dots placement.
        self.input.place(input_touch_area);
        self.prompt.place(prompt_area);
        // Remaining tries prompt
        self.attempts.place(attempts_area);
        self.warning.place(prompt_area);

        // Keypad placement
        self.keypad.place(keypad_area);

        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        match event {
            // Set up timer to switch off warning prompt.
            Event::Attach(_) => {
                if self.warning.is_some() {
                    self.warning_timer.start(ctx, Self::MAJOR_WARNING_TIMEOUT);
                }
                // Update the keypad state in the first event
                self.update_keypad_state(ctx);
            }
            // Hide warning, show major prompt.
            Event::Timer(_) if self.warning_timer.expire(event) => {
                self.warning = None;
            }

            _ => {}
        }

        match self.keypad.event(ctx, event) {
            Some(KeypadMsg::Key(idx)) => {
                // Add new pin digit
                if let ButtonContent::Text { text, .. } = self.keypad.get_key_content(idx) {
                    text.map(|text| {
                        self.input.push(text);
                    });
                    // Start the timer to show the last digit.
                    self.input
                        .last_digit_timer
                        .start(ctx, Self::LAST_DIGIT_TIMEOUT);
                    self.input.display_style = DisplayStyle::LastOnly;
                    // Update the keypad state.
                    self.update_keypad_state(ctx);
                    return None;
                }
            }
            Some(KeypadMsg::EraseShort) => {
                // Erase pin digit
                self.input.pop();
                self.update_keypad_state(ctx);
                return None;
            }
            Some(KeypadMsg::EraseLong) => {
                // Clear the entire pin
                self.input.clear();
                self.update_keypad_state(ctx);
                return None;
            }
            Some(KeypadMsg::Cancel) => {
                return Some(PinKeyboardMsg::Cancelled);
            }
            Some(KeypadMsg::Confirm) => {
                return Some(PinKeyboardMsg::Confirmed);
            }
            _ => {}
        }

        match self.input.event(ctx, event) {
            Some(PinInputMsg::TouchStart) => {
                // Disable keypad.
                self.update_keypad_state(ctx);
                return None;
            }
            Some(PinInputMsg::TouchEnd) => {
                // Enable keypad.
                self.update_keypad_state(ctx);
                return None;
            }
            _ => {}
        }

        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        let empty = self.input.is_empty();

        // Render prompt when the pin is empty
        if empty {
            if let Some(ref w) = self.warning {
                w.render(target);
            } else {
                self.prompt.render(target);
            }
            self.attempts.render(target);
        }

        // When the entire pin is shown, the input area might overlap the keypad so it
        // has to be rendered later
        match self.input.display_style {
            DisplayStyle::Shown if !empty => {
                self.keypad.render(target);
                self.input.render(target);
            }
            _ if !empty => {
                self.input.render(target);
                self.keypad.render(target);
            }
            _ => {
                self.keypad.render(target);
            }
        }
    }
}

#[derive(PartialEq, Debug, Copy, Clone)]
#[cfg_attr(feature = "ui_debug", derive(ufmt::derive::uDebug))]
pub enum PinInputMsg {
    TouchStart,
    TouchEnd,
}

struct PinInput {
    area: Rect,
    digits: ShortString,
    display_style: DisplayStyle,
    last_digit_timer: Timer,
    shown_area: Rect,
}

impl PinInput {
    const MAX_LENGTH: usize = 50; // max length of the pin
    const MAX_SHOWN_LEN: usize = 19; // max number of icons per line

    const TWITCH: i16 = 4;
    const SHOWN_STYLE: TextStyle = theme::TEXT_REGULAR
        .with_line_breaking(LineBreaking::BreakWordsNoHyphen)
        .with_chunks(Chunks::new(1, 8));
    const HIDDEN_STYLE: TextStyle = theme::TEXT_REGULAR;
    const SHOWN_TOUCH_OUTSET: Insets = Insets::bottom(200);
    const PIN_ICON: Icon = theme::ICON_DASH_VERTICAL;
    const ICON_SPACING: i16 = 12;

    fn new() -> Self {
        Self {
            area: Rect::zero(),
            digits: ShortString::new(),
            display_style: DisplayStyle::Hidden,
            last_digit_timer: Timer::new(),
            shown_area: Rect::zero(),
        }
    }

    fn width(&self) -> i16 {
        let ndots = self.pin().len().min(Self::MAX_SHOWN_LEN);
        let mut width = Self::PIN_ICON.toif.width() * (ndots as i16);
        // the last digit is wider than the icon so we count one extra space as well
        width += Self::ICON_SPACING * (ndots as i16);
        width
    }

    fn is_empty(&self) -> bool {
        self.digits.is_empty()
    }

    fn is_full(&self) -> bool {
        self.digits.len() >= Self::MAX_LENGTH
    }

    fn clear(&mut self) {
        self.digits.clear();
    }

    fn push(&mut self, text: &str) {
        // This could happen only when `self.pin` is full and wasn't able to accept all
        // of `text`
        unwrap!(self.digits.push_str(text));
    }

    fn pop(&mut self) {
        self.digits.pop();
    }

    fn pin(&self) -> &str {
        &self.digits
    }

    fn update_shown_area(&mut self) {
        // The area where the pin is shown
        let mut shown_area = self.area.inset(KEYBOARD_INPUT_INSETS);

        // Extend the shown area until the text fits
        while let LayoutFit::OutOfBounds { .. } = TextLayout::new(Self::SHOWN_STYLE)
            .with_align(Alignment::Start)
            .with_bounds(shown_area.inset(SHOWN_INSETS))
            .fit_text(self.pin())
        {
            shown_area =
                shown_area.outset(Insets::bottom(Self::SHOWN_STYLE.text_font.line_height()));
        }

        self.shown_area = shown_area;
    }

    fn render_shown<'s>(&self, target: &mut impl Renderer<'s>) {
        // Make sure the pin should be shown
        debug_assert_eq!(self.display_style, DisplayStyle::Shown);

        let base_shown_area = self.area.inset(KEYBOARD_INPUT_INSETS);
        let multiline_pin = self.shown_area.height() > base_shown_area.height();
        let alignment = if multiline_pin {
            // Multi-line pin is left aligned
            Alignment::Start
        } else {
            // FIXME: because of #5623, the chunkified PINs cannot be centered
            Alignment::Start
        };

        Bar::new(self.shown_area)
            .with_bg(theme::GREY_SUPER_DARK)
            .with_radius(KEYBOARD_INPUT_RADIUS)
            .render(target);

        TextLayout::new(Self::SHOWN_STYLE)
            .with_bounds(self.shown_area.inset(SHOWN_INSETS))
            .with_align(alignment)
            .render_text(self.pin(), target, true);
    }

    fn render_hidden<'s>(&self, target: &mut impl Renderer<'s>) {
        debug_assert_ne!(self.display_style, DisplayStyle::Shown);

        let hidden_area: Rect = self.area.inset(KEYBOARD_INPUT_INSETS);
        let pin_len = self.pin().len();
        let last_digit = self.display_style == DisplayStyle::LastOnly;

        let mut cursor = hidden_area.center().ofs(Offset::x(self.width() / 2).neg());

        // Render only when there are characters
        if pin_len == 0 {
            return;
        }
        // Number of visible icons + characters
        let visible_len = pin_len.min(Self::MAX_SHOWN_LEN);
        // Number of visible icons
        let visible_icons = visible_len - last_digit as usize;

        // Jiggle when overflowed.
        if pin_len > visible_len && pin_len % 2 == 0 && self.display_style != DisplayStyle::Shown {
            cursor.x += Self::TWITCH;
        }

        let mut char_idx = 0;

        // Greyed out overflowing icons
        for (i, &fg_color) in FADING_ICON_COLORS.iter().enumerate() {
            if pin_len > visible_len + (FADING_ICON_COUNT - 1 - i) {
                ToifImage::new(cursor, Self::PIN_ICON.toif)
                    .with_align(Alignment2D::CENTER_LEFT)
                    .with_fg(fg_color)
                    .render(target);
                cursor.x += Self::ICON_SPACING + Self::PIN_ICON.toif.width();
                char_idx += 1;
            }
        }

        if visible_icons > 0 {
            // Classical icons
            for _ in char_idx..visible_icons {
                ToifImage::new(cursor, Self::PIN_ICON.toif)
                    .with_align(Alignment2D::CENTER_LEFT)
                    .with_fg(Self::HIDDEN_STYLE.text_color)
                    .render(target);
                cursor.x += Self::ICON_SPACING + Self::PIN_ICON.toif.width();
            }
        }

        if last_digit {
            // This should not fail because pin_len > 0
            let last = &self.digits.as_str()[(pin_len - 1)..pin_len];

            // Adapt y position for the character
            cursor.y += Self::HIDDEN_STYLE.text_font.visible_text_height("1") / 2;

            // Paint the last character
            Text::new(cursor, last, Self::HIDDEN_STYLE.text_font)
                .with_align(Alignment::Start)
                .with_fg(Self::HIDDEN_STYLE.text_color)
                .render(target);
        }
    }
}

impl Component for PinInput {
    type Msg = PinInputMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.area = bounds;
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        // No touch events are handled when the input is empty
        if self.is_empty() {
            return None;
        }

        // Extend the pin area downward to allow touch input without the finger
        // covering the passphrase
        let extended_shown_area = self
            .shown_area
            .outset(Self::SHOWN_TOUCH_OUTSET)
            .clamp(SCREEN);

        match event {
            // Return touch start if the touch is detected inside the touchable area
            Event::Touch(TouchEvent::TouchStart(pos)) if self.area.contains(pos) => {
                // Stop the last char timer
                self.last_digit_timer.stop();
                // Show the entire pin on the touch start
                self.display_style = DisplayStyle::Shown;
                self.update_shown_area();
                return Some(PinInputMsg::TouchStart);
            }
            // Return touch end if the touch end is detected inside the visible area
            Event::Touch(TouchEvent::TouchEnd(pos))
                if extended_shown_area.contains(pos)
                    && self.display_style == DisplayStyle::Shown =>
            {
                self.display_style = DisplayStyle::Hidden;
                return Some(PinInputMsg::TouchEnd);
            }
            // Return touch end if the touch moves out of the visible area
            Event::Touch(TouchEvent::TouchMove(pos))
                if !extended_shown_area.contains(pos)
                    && self.display_style == DisplayStyle::Shown =>
            {
                self.display_style = DisplayStyle::Hidden;
                return Some(PinInputMsg::TouchEnd);
            }
            // Timeout for showing the last digit.
            Event::Timer(_) if self.last_digit_timer.expire(event) => {
                // Hide the PIN
                self.display_style = DisplayStyle::Hidden;
                ctx.request_paint();
            }
            _ => {}
        };
        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        if !self.digits.is_empty() {
            match self.display_style {
                DisplayStyle::Shown => self.render_shown(target),
                _ => self.render_hidden(target),
            }
        }
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for PinKeyboard<'_> {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("PinKeyboard");
        // So that debuglink knows the locations of the buttons
        let mut digits_order = ShortString::new();

        for idx in 0..10 {
            let btn_content = self.keypad.get_key_content(idx);
            if let ButtonContent::Text { text, .. } = btn_content {
                text.map(|text| {
                    unwrap!(digits_order.push_str(text));
                });
            }
        }
        let display_style = uformat!("{:?}", self.input.display_style);
        t.string("digits_order", digits_order.as_str().into());
        t.string("pin", self.input.pin().into());
        t.string("display_style", display_style.as_str().into());
    }
}
