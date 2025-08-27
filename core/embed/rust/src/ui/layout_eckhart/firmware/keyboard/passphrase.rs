use crate::{
    strutil::TString,
    time::Duration,
    ui::{
        component::{
            text::{
                common::TextBox,
                layout::{LayoutFit, LineBreaking},
                TextStyle,
            },
            Component, Event, EventCtx, TextLayout, Timer,
        },
        display::Icon,
        event::TouchEvent,
        geometry::{Alignment, Alignment2D, Insets, Offset, Rect},
        shape::{Bar, Renderer, Text, ToifImage},
        util::DisplayStyle,
    },
};

use super::super::{
    constant::SCREEN,
    keyboard::{
        common::{
            render_pending_marker, MultiTapKeyboard, FADING_ICON_COLORS, FADING_ICON_COUNT,
            KEYBOARD_INPUT_INSETS, KEYBOARD_INPUT_RADIUS, SHOWN_INSETS,
        },
        keypad::{ButtonState, KeypadState},
    },
    theme, StringInput, StringInputMsg,
};

pub struct PassphraseInput {
    area: Rect,
    textbox: TextBox,
    display_style: DisplayStyle,
    last_char_timer: Timer,
    shown_area: Rect,
    max_len: usize,
    multi_tap: MultiTapKeyboard,
    allow_cancel: bool,
    allow_empty: bool,
}

impl PassphraseInput {
    const TWITCH: i16 = 4;
    const STYLE: TextStyle =
        theme::TEXT_REGULAR.with_line_breaking(LineBreaking::BreakWordsNoHyphen);
    const SHOWN_TOUCH_OUTSET: Insets = Insets::bottom(200);
    const ICON: Icon = theme::ICON_DASH_VERTICAL;
    const ICON_WIDTH: i16 = Self::ICON.toif.width();
    const ICON_SPACE: i16 = 12;
    const MAX_SHOWN_LEN: usize = 13; // max number of icons per line
    const LAST_DIGIT_TIMEOUT: Duration = Duration::from_secs(1);

    pub fn new(max_len: usize, allow_cancel: bool, allow_empty: bool) -> Self {
        Self {
            area: Rect::zero(),
            textbox: TextBox::empty(max_len),
            display_style: DisplayStyle::Hidden,
            last_char_timer: Timer::new(),
            shown_area: Rect::zero(),
            max_len,
            multi_tap: MultiTapKeyboard::new(),
            allow_cancel,
            allow_empty,
        }
    }

    fn update_shown_area(&mut self) {
        // The area where the passphrase is shown
        let mut shown_area = Rect::from_top_left_and_size(
            self.area.top_left(),
            Offset::new(SCREEN.width(), self.area.height()),
        )
        .inset(KEYBOARD_INPUT_INSETS);

        // Extend the shown area until the text fits
        while let LayoutFit::OutOfBounds { .. } = TextLayout::new(Self::STYLE)
            .with_align(Alignment::Start)
            .with_bounds(shown_area.inset(SHOWN_INSETS))
            .fit_text(self.content())
        {
            shown_area = shown_area.outset(Insets::bottom(Self::STYLE.text_font.line_height()));
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

        TextLayout::new(Self::STYLE)
            .with_bounds(self.shown_area.inset(SHOWN_INSETS))
            .with_align(Alignment::Start)
            .render_text(self.content(), target, true);
    }

    fn render_hidden<'s>(&self, target: &mut impl Renderer<'s>) {
        debug_assert_ne!(self.display_style, DisplayStyle::Shown);

        let hidden_area: Rect = self.area.inset(KEYBOARD_INPUT_INSETS);
        let pp_len = self.content().len();
        let last_char = self.display_style != DisplayStyle::Hidden;

        let mut cursor = hidden_area.left_center().ofs(Offset::x(12));

        // Render only when there are characters
        if pp_len == 0 {
            return;
        }
        // Number of visible icons + characters
        let visible_len = pp_len.min(Self::MAX_SHOWN_LEN);
        // Number of visible icons
        let visible_icons = visible_len - last_char as usize;

        // Jiggle when overflowed.
        if pp_len > visible_len && pp_len % 2 == 0 && self.display_style != DisplayStyle::Shown {
            cursor.x += Self::TWITCH;
        }

        let mut char_idx = 0;

        // Greyed out overflowing icons
        for (i, &fg_color) in FADING_ICON_COLORS.iter().enumerate() {
            if pp_len > visible_len + (FADING_ICON_COUNT - 1 - i) {
                ToifImage::new(cursor, Self::ICON.toif)
                    .with_align(Alignment2D::CENTER_LEFT)
                    .with_fg(fg_color)
                    .render(target);
                cursor.x += Self::ICON_SPACE + Self::ICON_WIDTH;
                char_idx += 1;
            }
        }

        if visible_icons > 0 {
            // Classical dot(s)
            for _ in char_idx..visible_icons {
                ToifImage::new(cursor, Self::ICON.toif)
                    .with_align(Alignment2D::CENTER_LEFT)
                    .with_fg(Self::STYLE.text_color)
                    .render(target);
                cursor.x += Self::ICON_SPACE + Self::ICON_WIDTH;
            }
        }

        if last_char {
            // This should not fail because pp_len > 0
            let last = &self.content()[(pp_len - 1)..pp_len];

            // Adapt x and y positions for the character
            cursor.y += Self::STYLE.text_font.visible_text_height("1") / 2;

            // Paint the last character
            Text::new(cursor, last, Self::STYLE.text_font)
                .with_align(Alignment::Start)
                .with_fg(Self::STYLE.text_color)
                .render(target);

            // Paint the pending marker.
            if self.display_style == DisplayStyle::LastWithMarker {
                render_pending_marker(
                    target,
                    cursor,
                    last,
                    Self::STYLE.text_font,
                    Self::STYLE.text_color,
                );
            }
        }
    }
}

impl StringInput for PassphraseInput {
    fn on_key_click(&mut self, ctx: &mut EventCtx, idx: usize, text: TString<'static>) {
        let edit = text.map(|c| self.multi_tap.click_key(ctx, idx, c));
        self.textbox.apply(ctx, edit);
        if text.len() == 1 {
            // If the key has just one character, it is immediately applied and the last
            // digit timer should be started
            self.display_style = DisplayStyle::LastOnly;
            self.last_char_timer.start(ctx, Self::LAST_DIGIT_TIMEOUT);
        } else {
            // multi tap timer is runnig, the last digit timer should be stopped
            self.last_char_timer.stop();
            self.display_style = DisplayStyle::LastWithMarker;
        }
    }

    fn on_erase(&mut self, ctx: &mut EventCtx, long_erase: bool) {
        self.multi_tap.clear_pending_state(ctx);
        if long_erase {
            self.textbox.clear(ctx);
        } else {
            self.textbox.delete_last(ctx);
        }
        self.display_style = DisplayStyle::Hidden;
    }

    fn get_keypad_state(&self) -> KeypadState {
        if self.display_style == DisplayStyle::Shown {
            // Disable the entire active keypad
            KeypadState {
                back: ButtonState::Hidden,
                erase: ButtonState::Disabled,
                cancel: ButtonState::Hidden,
                confirm: ButtonState::Disabled,
                keys: ButtonState::Disabled,
                override_key: None,
            }
        } else if self.is_full() {
            // Disable all except of confirm, erase and the pending key if there is some
            let override_key = self
                .multi_tap
                .pending_key()
                .map(|k| (k, ButtonState::Enabled));

            KeypadState {
                back: ButtonState::Hidden,
                erase: ButtonState::Enabled,
                cancel: ButtonState::Hidden,
                confirm: ButtonState::Enabled,
                keys: ButtonState::Disabled,
                override_key,
            }
        } else if self.is_empty() {
            // Disable all except of confirm and erase buttons
            KeypadState {
                back: ButtonState::Hidden,
                erase: ButtonState::Hidden,
                cancel: if self.allow_cancel {
                    ButtonState::Enabled
                } else {
                    ButtonState::Hidden
                },
                confirm: if self.allow_empty {
                    ButtonState::Enabled
                } else {
                    ButtonState::Disabled
                },
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

    fn on_page_change(&mut self, ctx: &mut EventCtx) {
        if self.multi_tap.pending_key().is_some() {
            // Clear the pending state.
            self.multi_tap.clear_pending_state(ctx);
            self.display_style = DisplayStyle::LastOnly;
            // the character has been added, show it for a bit and then hide it
            self.last_char_timer.start(ctx, Self::LAST_DIGIT_TIMEOUT);
        }
    }

    fn content(&self) -> &str {
        self.textbox.content()
    }

    fn is_full(&self) -> bool {
        self.textbox.len() >= self.max_len
    }

    fn might_overlap_keypad(&self) -> bool {
        self.display_style == DisplayStyle::Shown
    }
}

impl Component for PassphraseInput {
    type Msg = StringInputMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.area = bounds;
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        // No touch events are handled when the textbox is empty
        if self.is_empty() {
            return None;
        }

        // Extend the passphrase area downward to allow touch input without the finger
        // covering the passphrase
        let extended_shown_area = self
            .shown_area
            .outset(Self::SHOWN_TOUCH_OUTSET)
            .clamp(SCREEN);

        match event {
            Event::Timer(_) if self.multi_tap.timeout_event(event) => {
                self.multi_tap.clear_pending_state(ctx);
                self.last_char_timer.start(ctx, Self::LAST_DIGIT_TIMEOUT);
                self.display_style = DisplayStyle::LastOnly;
                // Disable keypad when the passphrase reached the max length
                if self.is_full() {
                    return Some(StringInputMsg::UpdateKeypad);
                }
                return None;
            }
            // Return touch start if the touch is detected inside the touchable area
            Event::Touch(TouchEvent::TouchStart(pos)) if self.area.contains(pos) => {
                self.multi_tap.clear_pending_state(ctx);
                // Stop the last char timer
                self.last_char_timer.stop();
                // Show the entire passphrase on the touch start
                self.display_style = DisplayStyle::Shown;
                self.update_shown_area();
                return Some(StringInputMsg::UpdateKeypad);
            }
            // Return touch end if the touch end is detected inside the visible area
            Event::Touch(TouchEvent::TouchEnd(pos))
                if extended_shown_area.contains(pos)
                    && self.display_style == DisplayStyle::Shown =>
            {
                self.multi_tap.clear_pending_state(ctx);
                self.display_style = DisplayStyle::Hidden;
                return Some(StringInputMsg::UpdateKeypad);
            }
            // Return touch end if the touch moves out of the visible area
            Event::Touch(TouchEvent::TouchMove(pos))
                if !extended_shown_area.contains(pos)
                    && self.display_style == DisplayStyle::Shown =>
            {
                self.multi_tap.clear_pending_state(ctx);
                self.display_style = DisplayStyle::Hidden;
                return Some(StringInputMsg::UpdateKeypad);
            }
            // Timeout for showing the last char.
            Event::Timer(_) if self.last_char_timer.expire(event) => {
                self.display_style = DisplayStyle::Hidden;
                ctx.request_paint();
            }
            _ => {}
        };
        None
    }

    fn render<'s>(&self, target: &mut impl Renderer<'s>) {
        // Don't render if the input is empty
        if self.is_empty() {
            return;
        }

        match self.display_style {
            DisplayStyle::Shown => self.render_shown(target),
            _ => self.render_hidden(target),
        }
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for PassphraseInput {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("PassphraseInput");
        t.string("content", self.content().into());
        let display_style = uformat!("{:?}", self.display_style);
        t.string("display_style", display_style.as_str().into());
        t.bool("allow_empty", self.allow_empty);
        t.bool("allow_cancel", self.allow_cancel);
    }
}
