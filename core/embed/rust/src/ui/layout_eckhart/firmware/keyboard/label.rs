use crate::{
    strutil::TString,
    ui::{
        component::{
            text::{
                common::TextBox,
                layout::{LayoutFit, LineBreaking},
                TextStyle,
            },
            Component, Event, EventCtx, TextLayout,
        },
        event::TouchEvent,
        geometry::{Alignment, Insets, Offset, Rect},
        shape::{Bar, Renderer, Text},
        util::long_line_content_with_ellipsis,
    },
};

use super::super::{
    constant::SCREEN,
    keyboard::{
        common::{
            render_pending_marker, MultiTapKeyboard, KEYBOARD_INPUT_INSETS, KEYBOARD_INPUT_RADIUS,
            SHOWN_INSETS,
        },
        keypad::{ButtonState, KeypadState},
    },
    theme, StringInput, StringInputMsg,
};

#[derive(PartialEq, Debug, Copy, Clone)]
#[cfg_attr(feature = "ui_debug", derive(ufmt::derive::uDebug))]
enum LabelDisplayStyle {
    /// A part that fits on one line
    OneLine,
    /// One line with the last pending character.
    OneLineWithMarker,
    /// The complete string is shown in the input area.
    Complete,
}

pub struct LabelInput {
    area: Rect,
    textbox: TextBox,
    display_style: LabelDisplayStyle,
    shown_area: Rect,
    max_len: usize,
    multi_tap: MultiTapKeyboard,
    allow_cancel: bool,
    allow_empty: bool,
}

impl LabelInput {
    const STYLE: TextStyle =
        theme::TEXT_REGULAR.with_line_breaking(LineBreaking::BreakWordsNoHyphen);
    const SHOWN_TOUCH_OUTSET: Insets = Insets::bottom(200);
    const ONE_LINE_INSETS: Insets = Insets::new(
        KEYBOARD_INPUT_INSETS.top,
        0,
        KEYBOARD_INPUT_INSETS.bottom,
        KEYBOARD_INPUT_INSETS.left,
    );

    pub fn new(
        max_len: usize,
        prefill: Option<TString<'static>>,
        allow_cancel: bool,
        allow_empty: bool,
    ) -> Self {
        let textbox = if let Some(prefill) = prefill {
            prefill.map(|s| TextBox::new(s, max_len))
        } else {
            TextBox::empty(max_len)
        };
        Self {
            area: Rect::zero(),
            textbox,
            display_style: LabelDisplayStyle::OneLine,
            shown_area: Rect::zero(),
            max_len,
            multi_tap: MultiTapKeyboard::new(),
            allow_cancel,
            allow_empty,
        }
    }

    fn update_shown_area(&mut self) {
        // The area where the label is shown
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

    fn render_complete<'s>(&self, target: &mut impl Renderer<'s>) {
        // Make sure the entire label should be shown
        debug_assert_eq!(self.display_style, LabelDisplayStyle::Complete);

        Bar::new(self.shown_area)
            .with_bg(theme::GREY_SUPER_DARK)
            .with_radius(KEYBOARD_INPUT_RADIUS)
            .render(target);

        TextLayout::new(Self::STYLE)
            .with_bounds(self.shown_area.inset(SHOWN_INSETS))
            .with_align(Alignment::Start)
            .render_text(self.content(), target, true);
    }

    fn render_one_line<'s>(&self, target: &mut impl Renderer<'s>) {
        debug_assert_ne!(self.display_style, LabelDisplayStyle::Complete);

        let area: Rect = self.area.inset(Self::ONE_LINE_INSETS);

        // Find out how much text can fit into the textbox.
        // Accounting for the pending marker, which draws itself one pixel longer than
        // the last character
        let available_area_width = area.width() - 1;
        let text_to_display = long_line_content_with_ellipsis(
            self.content(),
            "...",
            Self::STYLE.text_font,
            available_area_width,
        );

        let cursor = area.left_center().ofs(Offset::new(
            8,
            Self::STYLE.text_font.visible_text_height("1") / 2,
        ));

        Text::new(cursor, &text_to_display, Self::STYLE.text_font)
            .with_fg(Self::STYLE.text_color)
            .render(target);

        // Paint the pending marker.
        if self.display_style == LabelDisplayStyle::OneLineWithMarker {
            render_pending_marker(
                target,
                cursor,
                &text_to_display,
                Self::STYLE.text_font,
                Self::STYLE.text_color,
            );
        }
    }
}

impl StringInput for LabelInput {
    fn on_key_click(&mut self, ctx: &mut EventCtx, idx: usize, text: TString<'static>) {
        let edit = text.map(|c| self.multi_tap.click_key(ctx, idx, c));
        self.textbox.apply(ctx, edit);
        if text.len() == 1 {
            // If the key has just one character, it is immediately applied
            self.display_style = LabelDisplayStyle::OneLine;
        } else {
            // multi tap timer is running, the marker should be shown
            self.display_style = LabelDisplayStyle::OneLineWithMarker;
        }
    }

    fn on_erase(&mut self, ctx: &mut EventCtx, long_erase: bool) {
        self.multi_tap.clear_pending_state(ctx);
        if long_erase {
            self.textbox.clear(ctx);
        } else {
            self.textbox.delete_last(ctx);
        }
        self.display_style = LabelDisplayStyle::OneLine;
    }

    fn get_keypad_state(&self) -> KeypadState {
        if self.display_style == LabelDisplayStyle::Complete {
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
        // Clear the pending state.
        self.multi_tap.clear_pending_state(ctx);
        self.display_style = LabelDisplayStyle::OneLine;
    }

    fn content(&self) -> &str {
        self.textbox.content()
    }

    fn is_full(&self) -> bool {
        self.textbox.len() >= self.max_len
    }

    fn might_overlap_keypad(&self) -> bool {
        self.display_style == LabelDisplayStyle::Complete
    }
}

impl Component for LabelInput {
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
                self.display_style = LabelDisplayStyle::OneLine;
                // Return update message to disable keypad when the passphrase reached the max
                // length
                if self.is_full() {
                    return Some(StringInputMsg::UpdateKeypad);
                }
                return None;
            }
            // Return update message to to disable keypad if the touch is detected inside the
            // touchable area
            Event::Touch(TouchEvent::TouchStart(pos)) if self.area.contains(pos) => {
                self.multi_tap.clear_pending_state(ctx);
                // Show the entire label on the touch start
                self.display_style = LabelDisplayStyle::Complete;
                self.update_shown_area();
                return Some(StringInputMsg::UpdateKeypad);
            }
            // Return update message to to re-enable keypad if the touch end is detected inside the
            // touchable area
            Event::Touch(TouchEvent::TouchEnd(pos))
                if extended_shown_area.contains(pos)
                    && self.display_style == LabelDisplayStyle::Complete =>
            {
                self.multi_tap.clear_pending_state(ctx);
                self.display_style = LabelDisplayStyle::OneLine;
                return Some(StringInputMsg::UpdateKeypad);
            }
            // Return update message to to re-enable keypad if the touch moves out of the visible
            // area
            Event::Touch(TouchEvent::TouchMove(pos))
                if !extended_shown_area.contains(pos)
                    && self.display_style == LabelDisplayStyle::Complete =>
            {
                self.multi_tap.clear_pending_state(ctx);
                self.display_style = LabelDisplayStyle::OneLine;
                return Some(StringInputMsg::UpdateKeypad);
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
            LabelDisplayStyle::Complete => self.render_complete(target),
            _ => self.render_one_line(target),
        }
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for LabelInput {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("LabelInput");
        t.string("content", self.content().into());
        let display_style = uformat!("{:?}", self.display_style);
        t.string("display_style", display_style.as_str().into());
        t.bool("allow_empty", self.allow_empty);
        t.bool("allow_cancel", self.allow_cancel);
    }
}
