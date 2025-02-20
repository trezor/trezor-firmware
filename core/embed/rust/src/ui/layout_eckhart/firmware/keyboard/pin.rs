use crate::{
    strutil::{ShortString, TString},
    time::Duration,
    ui::{
        component::{
            text::{
                layout::{Chunks, LayoutFit, LineBreaking},
                TextStyle,
            },
            Component, Event, EventCtx, Label, TextLayout, Timer,
        },
        display::Icon,
        event::TouchEvent,
        geometry::{Alignment, Alignment2D, Insets, Offset, Rect},
        shape::{Bar, Renderer, Text, ToifImage},
    },
};

use super::{
    super::super::{component::ButtonContent, constant::SCREEN, theme},
    common::{
        DisplayStyle, FADING_ICON_COLORS, FADING_ICON_COUNT, INPUT_TOUCH_HEIGHT,
        KEYBOARD_INPUT_INSETS, KEYBOARD_INPUT_RADIUS, KEYPAD_VISIBLE_HEIGHT,
    },
    keypad::{ButtonState, Keypad, KeypadMsg, KeypadState},
};

pub enum PinKeyboardMsg {
    Confirmed,
    Cancelled,
}

pub struct PinKeyboard<'a> {
    allow_cancel: bool,
    major_prompt: Label<'a>,
    minor_prompt: Label<'a>,
    major_warning: Option<Label<'a>>,
    keypad: Keypad,
    input: PinInput,
    warning_timer: Timer,
}

impl<'a> PinKeyboard<'a> {
    const LAST_DIGIT_TIMEOUT_S: u32 = 1;

    pub fn new(
        major_prompt: TString<'a>,
        minor_prompt: TString<'a>,
        major_warning: Option<TString<'a>>,
        allow_cancel: bool,
    ) -> Self {
        Self {
            allow_cancel,
            major_prompt: Label::left_aligned(major_prompt, theme::TEXT_SMALL)
                .vertically_centered(),
            minor_prompt: Label::right_aligned(minor_prompt, theme::TEXT_SMALL)
                .vertically_centered(),
            major_warning: major_warning
                .map(|text| Label::left_aligned(text, theme::TEXT_SMALL).vertically_centered()),
            input: PinInput::new(theme::TEXT_MONO_LIGHT),
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
                    }
                } else {
                    KeypadState {
                        back: ButtonState::Hidden,
                        erase: ButtonState::Enabled,
                        cancel: ButtonState::Hidden,
                        confirm: ButtonState::Enabled,
                        keys: ButtonState::Enabled,
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

        // Prompts and PIN dots placement.
        self.input.place(input_touch_area);
        self.major_prompt
            .place(input_touch_area.inset(KEYBOARD_INPUT_INSETS));
        self.minor_prompt
            .place(input_touch_area.inset(KEYBOARD_INPUT_INSETS));
        self.major_warning
            .as_mut()
            .map(|c| c.place(input_touch_area));

        // Keypad placement
        self.keypad.place(keypad_area);

        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        match event {
            // Set up timer to switch off warning prompt.
            Event::Attach(_) => {
                if self.major_warning.is_some() {
                    self.warning_timer.start(ctx, Duration::from_secs(2));
                }
                // Update the keypad state in the first event
                self.update_keypad_state(ctx);
            }
            // Hide warning, show major prompt.
            Event::Timer(_) if self.warning_timer.expire(event) => {
                self.major_warning = None;
            }

            _ => {}
        }

        match self.keypad.event(ctx, event) {
            Some(KeypadMsg::Key(idx)) => {
                // Add new pin digit
                if let ButtonContent::Text(text) = self.keypad.get_key_content(idx) {
                    text.map(|text| {
                        self.input.push(text);
                    });
                    // Start the timer to show the last digit.
                    self.input
                        .last_digit_timer
                        .start(ctx, Duration::from_secs(Self::LAST_DIGIT_TIMEOUT_S));
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
            if let Some(ref w) = self.major_warning {
                w.render(target);
            } else {
                self.major_prompt.render(target);
            }
            self.minor_prompt.render(target);
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
    style: TextStyle,
    digits: ShortString,
    display_style: DisplayStyle,
    last_digit_timer: Timer,
    shown_area: Rect,
}

impl PinInput {
    const MAX_LENGTH: usize = 50; // max length of the pin
    const MAX_SHOWN_LEN: usize = 19; // max number of icons per line

    const TWITCH: i16 = 4;
    const SHOWN_PADDING: i16 = 24;
    const SHOWN_STYLE: TextStyle = theme::TEXT_MEDIUM
        .with_line_breaking(LineBreaking::BreakWordsNoHyphen)
        .with_chunks(Chunks::new(1, 8));
    const PIN_ICON: Icon = theme::ICON_DASH_VERTICAL;
    const ICON_WIDTH: i16 = Self::PIN_ICON.toif.width();
    const ICON_SPACE: i16 = 12;

    fn new(style: TextStyle) -> Self {
        Self {
            area: Rect::zero(),
            style,
            digits: ShortString::new(),
            display_style: DisplayStyle::Hidden,
            last_digit_timer: Timer::new(),
            shown_area: Rect::zero(),
        }
    }

    fn size(&self) -> Offset {
        let ndots = self.pin().len().min(Self::MAX_SHOWN_LEN);
        let mut width = Self::ICON_WIDTH * (ndots as i16);
        width += Self::ICON_SPACE * (ndots.saturating_sub(1) as i16);
        Offset::new(width, 6)
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
            .with_bounds(shown_area.inset(Insets::uniform(Self::SHOWN_PADDING)))
            .fit_text(self.pin())
        {
            shown_area = shown_area.outset(Insets::bottom(32));
        }

        self.shown_area = shown_area;
    }

    fn render_shown<'s>(&self, target: &mut impl Renderer<'s>) {
        // Make sure the pin should be shown
        debug_assert_eq!(self.display_style, DisplayStyle::Shown);

        Bar::new(self.shown_area)
            .with_bg(theme::GREY_SUPER_DARK)
            .with_radius(KEYBOARD_INPUT_RADIUS)
            .render(target);

        TextLayout::new(Self::SHOWN_STYLE)
            .with_bounds(self.shown_area.inset(Insets::uniform(Self::SHOWN_PADDING)))
            .with_align(Alignment::Start)
            .render_text(self.pin(), target);
    }

    fn render_hidden<'s>(&self, target: &mut impl Renderer<'s>) {
        debug_assert_ne!(self.display_style, DisplayStyle::Shown);

        let hidden_area: Rect = self.area.inset(KEYBOARD_INPUT_INSETS);
        let style = theme::TEXT_MEDIUM;
        let pin_len = self.pin().len();
        let last_digit = self.display_style == DisplayStyle::LastOnly;

        let mut cursor = self.size().snap(hidden_area.center(), Alignment2D::CENTER);

        // Render only when there are characters
        if pin_len > 0 {
            // Number of visible icons + characters
            let visible_len = pin_len.min(Self::MAX_SHOWN_LEN);
            // Number of visible icons
            let visible_icons = visible_len - last_digit as usize;

            // Jiggle when overflowed.
            if pin_len > visible_len
                && pin_len % 2 == 0
                && self.display_style != DisplayStyle::Shown
            {
                cursor.x += Self::TWITCH;
            }

            let mut char_idx = 0;

            // Greyed out overflowing icons
            for (i, &fg_color) in FADING_ICON_COLORS.iter().enumerate() {
                if pin_len > visible_len + (FADING_ICON_COUNT - 1 - i) {
                    ToifImage::new(cursor, Self::PIN_ICON.toif)
                        .with_align(Alignment2D::TOP_LEFT)
                        .with_fg(fg_color)
                        .render(target);
                    cursor.x += Self::ICON_SPACE + Self::ICON_WIDTH;
                    char_idx += 1;
                }
            }

            if visible_icons > 0 {
                // Classical icons
                for _ in char_idx..visible_icons {
                    ToifImage::new(cursor, Self::PIN_ICON.toif)
                        .with_align(Alignment2D::TOP_LEFT)
                        .with_fg(style.text_color)
                        .render(target);
                    cursor.x += Self::ICON_SPACE + Self::ICON_WIDTH;
                }
            }

            if last_digit {
                // This should not fail because all_chars > 0
                let last = &self.digits.as_str()[(pin_len - 1)..pin_len];

                // Adapt a and y positions for the character
                cursor.y = hidden_area.left_center().y + style.text_font.allcase_text_height() / 2;
                cursor.x -= style.text_font.text_width(last) / 2 - Self::ICON_WIDTH / 2;

                // Paint the last character
                Text::new(cursor, last, style.text_font)
                    .with_align(Alignment::Start)
                    .with_fg(style.text_color)
                    .render(target);
            }
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
                if self.shown_area.contains(pos) && self.display_style == DisplayStyle::Shown =>
            {
                self.display_style = DisplayStyle::Hidden;
                return Some(PinInputMsg::TouchEnd);
            }
            // Return touch end if the touch moves out of the visible area
            Event::Touch(TouchEvent::TouchMove(pos))
                if !self.shown_area.contains(pos) && self.display_style == DisplayStyle::Shown =>
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
            if let ButtonContent::Text(text) = btn_content {
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
