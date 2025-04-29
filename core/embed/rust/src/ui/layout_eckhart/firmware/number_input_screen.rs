use crate::{
    strutil::{self, ShortString, TString},
    time::Duration,
    translations::TR,
    ui::{
        component::{Component, Event, EventCtx, Label, Maybe, Never, Timer},
        geometry::{Alignment, Insets, Offset, Rect},
        shape::{self, Renderer},
        util::format_plural,
    },
};

use super::{
    super::{
        super::constant::SCREEN,
        component::{Button, ButtonMsg},
        fonts, theme,
    },
    ActionBar, ActionBarMsg, Header, HeaderMsg,
};

// Time conversion constants used to convert between different time units
const MIN_S: u32 = 60;
const HOUR_S: u32 = 3600;
const DAY_S: u32 = 86400;

pub enum NumberInputScreenMsg {
    Cancelled,
    Confirmed(u32),
    Menu,
}

pub struct NumberInputScreen {
    /// Screen header
    header: Header,
    /// Screeen description
    description: Label<'static>,
    /// Number input dialog
    number_input: NumberInput,
    /// Screen action bar
    action_bar: ActionBar,
}

impl NumberInputScreen {
    const DESCRIPTION_HEIGHT: i16 = 123;
    const INPUT_HEIGHT: i16 = 170;
    pub fn new(
        min: u32,
        max: u32,
        init_value: u32,
        text: TString<'static>,
        time_conversion: bool,
    ) -> Self {
        Self {
            header: Header::new(TString::empty()),
            action_bar: ActionBar::new_cancel_confirm(),
            number_input: NumberInput::new(min, max, init_value, time_conversion),
            description: Label::new(text, Alignment::Start, theme::TEXT_MEDIUM),
        }
    }

    pub fn with_header(mut self, header: Header) -> Self {
        self.header = header;
        self
    }

    pub fn value(&self) -> u32 {
        self.number_input.value
    }
}

impl Component for NumberInputScreen {
    type Msg = NumberInputScreenMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        // assert full screen
        debug_assert_eq!(bounds.height(), SCREEN.height());
        debug_assert_eq!(bounds.width(), SCREEN.width());

        let (header_area, rest) = bounds.split_top(Header::HEADER_HEIGHT);
        let (rest, action_bar_area) = rest.split_bottom(ActionBar::ACTION_BAR_HEIGHT);
        let (description_area, rest) = rest.split_top(Self::DESCRIPTION_HEIGHT);
        let (input_area, rest) = rest.split_top(Self::INPUT_HEIGHT);

        // Set touch expansion for the action bar not to overlap with the input area
        self.action_bar
            .set_touch_expansion(Insets::top(rest.height()));

        let description_area = description_area.inset(Insets::sides(24));

        self.header.place(header_area);
        self.description.place(description_area);
        self.number_input.place(input_area);
        self.action_bar.place(action_bar_area);

        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        self.number_input.event(ctx, event);

        if let Some(HeaderMsg::Menu) = self.header.event(ctx, event) {
            return Some(NumberInputScreenMsg::Menu);
        }

        if let Some(msg) = self.action_bar.event(ctx, event) {
            match msg {
                ActionBarMsg::Confirmed => {
                    return Some(NumberInputScreenMsg::Confirmed(self.value()))
                }
                ActionBarMsg::Cancelled => return Some(NumberInputScreenMsg::Cancelled),
                _ => {}
            }
        }

        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.header.render(target);
        self.description.render(target);
        self.number_input.render(target);
        self.action_bar.render(target);
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for NumberInputScreen {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("NumberInputScreen");
        t.child("number_input", &self.number_input);
        t.child("description", &self.description);
    }
}

struct NumberInput {
    area: Rect,
    dec: Maybe<Button>,
    inc: Maybe<Button>,
    min: u32,
    max: u32,
    value: u32,
    time_conversion: bool,
    hold_timer: Timer,
    counter: u32,
}

impl NumberInput {
    const BUTTON_PADDING: i16 = 10;
    const LABEL_OFFSET: i16 = 21;
    const BUTTON_SIZE: Offset = Offset::new(138, 130);
    const BORDER_PADDING: i16 = 24;
    const HOLD_TIMEOUT_S: u32 = 500;
    const BIG_INCREMENT: u32 = 10;
    const BIG_INCREMENT_THRESHOLD: u32 = 5;
    pub fn new(min: u32, max: u32, value: u32, time_conversion: bool) -> Self {
        let dec = Button::with_icon(theme::ICON_MINUS)
            .styled(theme::button_keyboard())
            .with_radius(12);
        let inc = Button::with_icon(theme::ICON_PLUS)
            .styled(theme::button_keyboard())
            .with_radius(12);
        let mut value = value.clamp(min, max);
        if time_conversion {
            value = Self::align_time_value(value);
        }
        Self {
            area: Rect::zero(),
            dec: Maybe::new(theme::BG, dec, value > min),
            inc: Maybe::new(theme::BG, inc, value < max),
            min,
            max,
            value,
            time_conversion,
            hold_timer: Timer::new(),
            counter: 0,
        }
    }

    fn handle_button_event(&mut self, msg: ButtonMsg, ctx: &mut EventCtx, is_increment: bool) {
        match msg {
            ButtonMsg::Clicked => {
                self.hold_timer.stop();
                if self.counter == 0 {
                    if is_increment {
                        self.increase(ctx);
                    } else {
                        self.decrease(ctx);
                    }
                }
                self.counter = 0;
            }
            ButtonMsg::Released => {
                self.hold_timer.stop();
                self.counter = 0;
            }
            ButtonMsg::Pressed => {
                self.hold_timer
                    .start(ctx, Duration::from_millis(Self::HOLD_TIMEOUT_S));
            }
            _ => {}
        }
    }

    fn increment_value(&mut self) {
        self.value = if self.time_conversion {
            if self.value < MIN_S {
                self.value.saturating_add(1).min(self.max)
            } else if self.value < HOUR_S {
                let aligned = (self.value / MIN_S) * MIN_S;
                aligned.saturating_add(MIN_S).min(self.max)
            } else if self.value < DAY_S {
                let aligned = (self.value / HOUR_S) * HOUR_S;
                aligned.saturating_add(HOUR_S).min(self.max)
            } else {
                let aligned = (self.value / DAY_S) * DAY_S;
                aligned.saturating_add(DAY_S).min(self.max)
            }
        } else {
            self.value.saturating_add(1).min(self.max)
        };
    }
    fn increase(&mut self, ctx: &mut EventCtx) {
        let n = if self.counter < Self::BIG_INCREMENT_THRESHOLD {
            1
        } else {
            Self::BIG_INCREMENT
        };
        let old = self.value;

        for _ in 0..n {
            self.increment_value();
        }

        if old != self.value {
            self.on_change(ctx);
        } else {
            self.on_saturation();
        }
    }

    fn decrement_value(&mut self) {
        self.value = if self.time_conversion {
            let aligned = Self::align_time_value(self.value);
            if aligned < MIN_S * 2 {
                aligned.saturating_sub(1).max(self.min)
            } else if aligned < HOUR_S * 2 {
                aligned.saturating_sub(MIN_S).max(self.min)
            } else if aligned < DAY_S * 2 {
                aligned.saturating_sub(HOUR_S).max(self.min)
            } else {
                aligned.saturating_sub(DAY_S).max(self.min)
            }
        } else {
            self.value.saturating_sub(1).max(self.min)
        };
    }

    fn decrease(&mut self, ctx: &mut EventCtx) {
        let n = if self.counter < Self::BIG_INCREMENT_THRESHOLD {
            1
        } else {
            Self::BIG_INCREMENT
        };

        let old = self.value;
        for _ in 0..n {
            self.decrement_value();
        }

        if old != self.value {
            self.on_change(ctx);
        } else {
            self.on_saturation();
        }
    }

    fn on_saturation(&mut self) {
        self.hold_timer.stop();
        self.counter = 0;
    }

    fn on_change(&mut self, ctx: &mut EventCtx) {
        if self.value > self.min {
            self.dec.show(ctx);
        } else {
            self.dec.hide(ctx);
            // If the value is saturated by a long hold, the button state is reset to
            // initial
            self.dec.inner_mut().enable(ctx);
        }

        if self.value < self.max {
            self.inc.show(ctx);
        } else {
            self.inc.hide(ctx);
            // If the value is saturated by a long hold, the button state must be reset
            self.inc.inner_mut().enable(ctx);
        }
        ctx.request_paint();
    }

    fn format_time_value(value: u32) -> (u32, Option<ShortString>) {
        let get_plural = |s: TString, value| s.map(|template| format_plural(template, value));

        if value < MIN_S {
            (
                value,
                Some(get_plural(TR::plurals__lock_after_x_seconds.into(), value)),
            )
        } else if value < HOUR_S {
            let minutes = value / MIN_S;
            (
                minutes,
                Some(get_plural(
                    TR::plurals__lock_after_x_minutes.into(),
                    minutes,
                )),
            )
        } else if value < DAY_S {
            let hours = value / HOUR_S;
            (
                hours,
                Some(get_plural(TR::plurals__lock_after_x_hours.into(), hours)),
            )
        } else {
            let days = value / DAY_S;
            (
                days,
                Some(get_plural(TR::plurals__lock_after_x_days.into(), days)),
            )
        }
    }

    fn align_to_unit(value: u32, unit: u32) -> u32 {
        (value / unit) * unit
    }

    fn align_time_value(value: u32) -> u32 {
        if value < MIN_S {
            value
        } else if value < HOUR_S {
            Self::align_to_unit(value, MIN_S)
        } else if value < DAY_S {
            Self::align_to_unit(value, HOUR_S)
        } else {
            Self::align_to_unit(value, DAY_S)
        }
    }

    fn render_borders<'s>(&'s self, target: &mut impl Renderer<'s>) {
        let borders = self.area.inset(Insets::sides(Self::BORDER_PADDING));
        // Render lines as bars with the with 1px
        let top_line =
            Rect::from_bottom_right_and_size(borders.top_right(), Offset::new(borders.width(), 1));
        let bottom_line =
            Rect::from_top_right_and_size(borders.bottom_right(), Offset::new(borders.width(), 1));

        shape::Bar::new(top_line)
            .with_fg(theme::GREY_EXTRA_DARK)
            .with_bg(theme::GREY_EXTRA_DARK)
            .render(target);

        shape::Bar::new(bottom_line)
            .with_fg(theme::GREY_EXTRA_DARK)
            .with_bg(theme::GREY_EXTRA_DARK)
            .render(target);
    }

    fn render_number<'s>(&'s self, target: &mut impl Renderer<'s>) {
        let mut buf = [0u8; 3];
        let (num, label) = if self.time_conversion {
            Self::format_time_value(self.value)
        } else {
            (self.value, None)
        };

        if let Some(num_str) = strutil::format_i64(num as i64, &mut buf) {
            let num_font = fonts::FONT_SATOSHI_EXTRALIGHT_72;
            let label_font = fonts::FONT_SATOSHI_REGULAR_22;

            let mut num_offset = Offset::y(num_font.allcase_text_height() / 2);
            if label.is_some() {
                num_offset = num_offset.sub(Offset::y(
                    label_font.allcase_text_height() / 2 + Self::LABEL_OFFSET,
                ));
            }
            shape::Text::new(self.area.center().ofs(num_offset), num_str, num_font)
                .with_align(Alignment::Center)
                .with_fg(theme::GREY)
                .render(target);

            if let Some(label) = label {
                let label_offset = num_offset.add(Offset::y(
                    label_font.allcase_text_height() + Self::LABEL_OFFSET,
                ));

                shape::Text::new(
                    self.area.center().ofs(label_offset),
                    label.as_str(),
                    label_font,
                )
                .with_align(Alignment::Center)
                .with_fg(theme::GREY)
                .render(target);
            }
        }
    }
}

impl Component for NumberInput {
    type Msg = Never;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.area = bounds;

        let button_bounds = self.area.inset(Insets::sides(Self::BUTTON_PADDING));
        // Equivalent to from_left_center_and_size
        let dec_bounds = Rect::from_center_and_size(
            button_bounds
                .left_center()
                .ofs(Offset::x(Self::BUTTON_SIZE.x / 2)),
            Self::BUTTON_SIZE,
        );
        // Equivalent to from_right_center_and_size
        let inc_bounds = Rect::from_center_and_size(
            button_bounds
                .right_center()
                .ofs(Offset::x(-Self::BUTTON_SIZE.x / 2)),
            Self::BUTTON_SIZE,
        );

        self.dec.place(dec_bounds);
        self.inc.place(inc_bounds);
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        // Hold timer expiration
        if self.hold_timer.expire(event) {
            // If the value is not saturated (button is pressed and visible),
            // increase/decrease the value and restart the timer
            if self.dec.is_visible() && self.dec.inner().is_pressed() {
                self.decrease(ctx);
                self.hold_timer
                    .start(ctx, Duration::from_millis(Self::HOLD_TIMEOUT_S));
                self.counter += 1;
                return None;
            } else if self.inc.is_visible() && self.inc.inner().is_pressed() {
                self.increase(ctx);
                self.hold_timer
                    .start(ctx, Duration::from_millis(Self::HOLD_TIMEOUT_S));
                self.counter += 1;
                return None;
            } else {
                self.on_saturation();
                return None;
            }
        }

        // Handle decrement button events
        if let Some(dec_event) = self.dec.event(ctx, event) {
            self.handle_button_event(dec_event, ctx, false);
            return None;
        }

        // Handle increment button events
        if let Some(inc_event) = self.inc.event(ctx, event) {
            self.handle_button_event(inc_event, ctx, true);
            return None;
        }

        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.render_borders(target);
        self.render_number(target);
        self.dec.render(target);
        self.inc.render(target);
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for NumberInput {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("NumberInput");
        t.int("value", self.value as i64);
    }
}

#[cfg(test)]
mod tests {
    use super::{super::super::constant::SCREEN, *};

    #[test]
    fn test_component_heights_fit_screen() {
        assert!(
            NumberInputScreen::DESCRIPTION_HEIGHT
                + NumberInputScreen::INPUT_HEIGHT
                + Header::HEADER_HEIGHT
                + ActionBar::ACTION_BAR_HEIGHT
                <= SCREEN.height(),
            "Components overflow the screen height",
        );
    }

    #[test]
    fn test_time_value_formatting() {
        assert_eq!(
            NumberInput::format_time_value(0),
            (0, Some(unwrap!(ShortString::try_from("seconds"))))
        );
        assert_eq!(
            NumberInput::format_time_value(1),
            (1, Some(unwrap!(ShortString::try_from("second"))))
        );
        assert_eq!(
            NumberInput::format_time_value(2),
            (2, Some(unwrap!(ShortString::try_from("seconds"))))
        );
        assert_eq!(
            NumberInput::format_time_value(60),
            (1, Some(unwrap!(ShortString::try_from("minute"))))
        );
        assert_eq!(
            NumberInput::format_time_value(120),
            (2, Some(unwrap!(ShortString::try_from("minutes"))))
        );
        assert_eq!(
            NumberInput::format_time_value(3540),
            (59, Some(unwrap!(ShortString::try_from("minutes"))))
        );
        assert_eq!(
            NumberInput::format_time_value(3600),
            (1, Some(unwrap!(ShortString::try_from("hour"))))
        );
        assert_eq!(
            NumberInput::format_time_value(7200),
            (2, Some(unwrap!(ShortString::try_from("hours"))))
        );
        assert_eq!(
            NumberInput::format_time_value(82800),
            (23, Some(unwrap!(ShortString::try_from("hours"))))
        );
        assert_eq!(
            NumberInput::format_time_value(86400),
            (1, Some(unwrap!(ShortString::try_from("day"))))
        );
    }

    #[test]
    fn test_align_time_value() {
        // Below 60 seconds stays the same
        assert_eq!(NumberInput::align_time_value(59), 59);
        // Minutes (60..3600)
        assert_eq!(NumberInput::align_time_value(61), 60);
        assert_eq!(NumberInput::align_time_value(119), 60);
        assert_eq!(NumberInput::align_time_value(3599), 3540);
        // Hours (3600..86400)
        assert_eq!(NumberInput::align_time_value(3601), 3600);
        assert_eq!(NumberInput::align_time_value(7199), 3600);
        assert_eq!(NumberInput::align_time_value(86399), 82800);
        // Days (86400+)
        assert_eq!(NumberInput::align_time_value(86400), 86400);
        assert_eq!(NumberInput::align_time_value(172801), 172800);
    }
}
