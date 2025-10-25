use crate::{
    strutil::{self, plural_form, ShortString, TString},
    time::Duration,
    translations::TR,
    ui::{
        component::{swipe_detect::SwipeConfig, Component, Event, EventCtx, Label, Maybe, Timer},
        flow::Swipable,
        geometry::{Alignment, Insets, Offset, Rect},
        shape::{self, Renderer},
        util::Pager,
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

pub enum ValueInputScreenMsg {
    Cancelled,
    Confirmed(u32),
    Changed(u32),
    Menu,
}

pub struct ValueInputScreen<T: ValueInput> {
    /// Screen header
    header: Header,
    /// Screeen description
    description: Label<'static>,
    /// Value input dialog
    input_dialog: ValueInputDialog<T>,
    /// Return message when the value is changed
    /// This is only used in the flows
    changed_value_handling: bool,
    /// Screen action bar
    action_bar: ActionBar,
}

impl<T: ValueInput> ValueInputScreen<T> {
    const DESCRIPTION_HEIGHT: i16 = 108;
    const INPUT_HEIGHT: i16 = 202;
    pub fn new(value: T, text: TString<'static>) -> Self {
        Self {
            header: Header::new(TString::empty()),
            action_bar: ActionBar::new_cancel_confirm(),
            input_dialog: ValueInputDialog::new(value),
            changed_value_handling: false,
            description: Label::new(text, Alignment::Start, theme::TEXT_MEDIUM),
        }
    }

    pub fn with_header(mut self, header: Header) -> Self {
        self.header = header;
        self
    }

    pub fn with_action_bar(mut self, action_bar: ActionBar) -> Self {
        self.action_bar = action_bar;
        self
    }

    pub fn with_changed_value_handling(mut self) -> Self {
        self.changed_value_handling = true;
        self
    }

    pub fn value(&self) -> u32 {
        self.input_dialog.value_input.num()
    }
}

impl<T: ValueInput> Component for ValueInputScreen<T> {
    type Msg = ValueInputScreenMsg;

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
        self.input_dialog.place(input_area);
        self.action_bar.place(action_bar_area);

        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if let Some(HeaderMsg::Menu) = self.header.event(ctx, event) {
            return Some(ValueInputScreenMsg::Menu);
        }

        if let Some(msg) = self.action_bar.event(ctx, event) {
            match msg {
                ActionBarMsg::Confirmed => {
                    return Some(ValueInputScreenMsg::Confirmed(self.value()))
                }
                ActionBarMsg::Cancelled => return Some(ValueInputScreenMsg::Cancelled),
                _ => {}
            }
        }

        self.input_dialog
            .event(ctx, event)
            .filter(|_| self.changed_value_handling)
            .map(ValueInputScreenMsg::Changed)
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.header.render(target);
        self.description.render(target);
        self.input_dialog.render(target);
        self.action_bar.render(target);
    }
}

#[cfg(feature = "micropython")]
impl<T: ValueInput> Swipable for ValueInputScreen<T> {
    fn get_swipe_config(&self) -> SwipeConfig {
        SwipeConfig::new()
    }

    fn get_pager(&self) -> Pager {
        Pager::single_page()
    }
}

#[cfg(feature = "ui_debug")]
impl<T: ValueInput> crate::trace::Trace for ValueInputScreen<T> {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("ValueInputScreen");
        t.child("description", &self.description);
        t.child("Header", &self.header);
        t.child("input_dialog", &self.input_dialog);
    }
}

struct ValueInputDialog<T: ValueInput> {
    area: Rect,
    dec: Maybe<Button>,
    inc: Maybe<Button>,
    value_input: T,
    hold_timer: Timer,
    counter: u32,
}

impl<T: ValueInput> ValueInputDialog<T> {
    const BUTTON_PADDING: i16 = 10;
    const LABEL_OFFSET: i16 = 21;
    const BUTTON_SIZE: Offset = Offset::new(138, 130);
    const BORDER_PADDING: i16 = 24;
    const HOLD_TIMEOUT_DURATION: Duration = Duration::from_millis(500);
    const BIG_INCREMENT: u32 = 10;
    const BIG_INCREMENT_THRESHOLD: u32 = 5;
    fn new(value_input: T) -> Self {
        let dec = Button::with_icon(theme::ICON_MINUS)
            .styled(theme::button_keyboard())
            .with_radius(12);
        let inc = Button::with_icon(theme::ICON_PLUS)
            .styled(theme::button_keyboard())
            .with_radius(12);
        Self {
            area: Rect::zero(),
            dec: Maybe::new(theme::BG, dec, !value_input.is_min()),
            inc: Maybe::new(theme::BG, inc, !value_input.is_max()),
            value_input,
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
                self.hold_timer.start(ctx, Self::HOLD_TIMEOUT_DURATION);
            }
            _ => {}
        }
    }

    fn increase(&mut self, ctx: &mut EventCtx) {
        let n = if self.counter < Self::BIG_INCREMENT_THRESHOLD {
            1
        } else {
            Self::BIG_INCREMENT
        };

        for _ in 0..n {
            self.value_input.increment();
        }

        self.on_change(ctx);
    }

    fn decrease(&mut self, ctx: &mut EventCtx) {
        let n = if self.counter < Self::BIG_INCREMENT_THRESHOLD {
            1
        } else {
            Self::BIG_INCREMENT
        };

        for _ in 0..n {
            self.value_input.decrement();
        }

        self.on_change(ctx);
        ctx.request_paint();
    }

    fn on_change(&mut self, ctx: &mut EventCtx) {
        if self.value_input.is_min() {
            self.dec.hide(ctx);
            // If the value is saturated by a long hold, the button state is reset to
            // initial
            self.dec.inner_mut().enable(ctx);
            self.on_saturation();
        } else {
            self.dec.show(ctx);
        }

        if self.value_input.is_max() {
            self.inc.hide(ctx);
            // If the value is saturated by a long hold, the button state must be reset
            self.inc.inner_mut().enable(ctx);
            self.on_saturation();
        } else {
            self.inc.show(ctx);
        }
    }

    fn on_saturation(&mut self) {
        self.hold_timer.stop();
        self.counter = 0;
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

        let (num, label) = self.value_input.repr();

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

impl<T: ValueInput> Component for ValueInputDialog<T> {
    type Msg = u32;

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
        let old_value = self.value_input.num();
        // Closure to return updated value if changed
        let return_if_changed = |new_value| {
            if old_value != new_value {
                Some(new_value)
            } else {
                None
            }
        };

        // Hold timer expiration
        if self.hold_timer.expire(event) {
            // If the value is not saturated (button is pressed and visible),
            // increase/decrease the value and restart the timer
            if self.dec.is_visible() && self.dec.inner().is_pressed() {
                self.decrease(ctx);
                self.hold_timer.start(ctx, Self::HOLD_TIMEOUT_DURATION);
                self.counter += 1;
                ctx.request_paint();
                return return_if_changed(self.value_input.num());
            } else if self.inc.is_visible() && self.inc.inner().is_pressed() {
                self.increase(ctx);
                self.hold_timer.start(ctx, Self::HOLD_TIMEOUT_DURATION);
                self.counter += 1;
                ctx.request_paint();
                return return_if_changed(self.value_input.num());
            } else {
                self.on_saturation();
                return None;
            }
        }

        // Handle decrement button events
        if let Some(dec_event) = self.dec.event(ctx, event) {
            self.handle_button_event(dec_event, ctx, false);
            return return_if_changed(self.value_input.num());
        }

        // Handle increment button events
        if let Some(inc_event) = self.inc.event(ctx, event) {
            self.handle_button_event(inc_event, ctx, true);
            return return_if_changed(self.value_input.num());
        }

        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.render_borders(target);
        self.dec.render(target);
        self.inc.render(target);
        self.render_number(target);
    }
}

#[cfg(feature = "ui_debug")]
impl<T: ValueInput> crate::trace::Trace for ValueInputDialog<T> {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("ValueInput");
        t.int("value", self.value_input.num() as i64);
    }
}

pub trait ValueInput {
    fn num(&self) -> u32;
    fn repr(&self) -> (u32, Option<ShortString>);
    fn increment(&mut self);
    fn decrement(&mut self);
    fn is_max(&self) -> bool;
    fn is_min(&self) -> bool;
}

pub struct NumberInput {
    value: u32,
    min: u32,
    max: u32,
}

impl ValueInput for NumberInput {
    fn num(&self) -> u32 {
        self.value
    }

    fn repr(&self) -> (u32, Option<ShortString>) {
        (self.value, None)
    }

    fn increment(&mut self) {
        self.value = self.value.saturating_add(1).min(self.max);
    }

    fn decrement(&mut self) {
        self.value = self.value.saturating_sub(1).max(self.min);
    }

    fn is_max(&self) -> bool {
        self.value == self.max
    }

    fn is_min(&self) -> bool {
        self.value == self.min
    }
}

impl NumberInput {
    pub fn new(min: u32, max: u32, value: u32) -> Self {
        Self {
            value: value.clamp(min, max),
            min,
            max,
        }
    }
}

pub struct DurationInput {
    duration: Duration,
    min: Duration,
    max: Duration,
}

impl ValueInput for DurationInput {
    fn num(&self) -> u32 {
        self.duration.to_millis()
    }

    fn repr(&self) -> (u32, Option<ShortString>) {
        let units = [
            (self.duration.to_days(), TR::plurals__lock_after_x_days),
            (self.duration.to_hours(), TR::plurals__lock_after_x_hours),
            (self.duration.to_mins(), TR::plurals__lock_after_x_minutes),
            (self.duration.to_secs(), TR::plurals__lock_after_x_seconds),
        ];

        for &(count, tr) in &units {
            if count > 0 {
                let plural =
                    TString::from_translation(tr).map(|template| plural_form(template, count));
                return (count, Some(plural));
            }
        }

        // This should never be reached unless duration is exactly 0
        (0, None)
    }

    fn increment(&mut self) {
        self.duration = unwrap!(self.duration.increment_unit()).min(self.max);
    }

    fn decrement(&mut self) {
        self.duration = unwrap!(self.duration.decrement_unit()).max(self.min);
    }

    fn is_max(&self) -> bool {
        self.duration == self.max
    }

    fn is_min(&self) -> bool {
        self.duration == self.min
    }
}

impl DurationInput {
    pub fn new(min: Duration, max: Duration, duration: Duration) -> Self {
        let max_crop = max.crop_to_largest_unit();
        let min_crop = min.crop_to_largest_unit();
        Self {
            duration: duration.clamp(min_crop, max_crop).crop_to_largest_unit(),
            min: min_crop,
            max: max_crop,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::{super::super::constant::SCREEN, *};

    #[test]
    fn test_component_heights_fit_screen() {
        assert!(
            ValueInputScreen::<DurationInput>::DESCRIPTION_HEIGHT
                + ValueInputScreen::<DurationInput>::INPUT_HEIGHT
                + Header::HEADER_HEIGHT
                + ActionBar::ACTION_BAR_HEIGHT
                <= SCREEN.height(),
            "Components overflow the screen height",
        );
    }
}
