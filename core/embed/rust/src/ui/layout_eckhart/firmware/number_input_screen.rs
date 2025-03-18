use crate::{
    strutil::{self, TString},
    translations::TR,
    ui::{
        component::{Component, Event, EventCtx, Label, Maybe, Never},
        geometry::{Alignment, Insets, Offset, Rect},
        shape::{self, Renderer},
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
    pub fn new(min: u32, max: u32, init_value: u32, text: TString<'static>) -> Self {
        Self {
            header: Header::new(TString::empty()),
            action_bar: ActionBar::new_double(
                Button::with_icon(theme::ICON_CROSS).styled(theme::button_cancel()),
                Button::with_text(TR::buttons__continue.into()),
            ),
            number_input: NumberInput::new(min, max, init_value),
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
}

impl NumberInput {
    const BUTTON_PADDING: i16 = 10;
    const BUTTON_SIZE: Offset = Offset::new(138, 130);
    const BORDER_PADDING: i16 = 24;
    pub fn new(min: u32, max: u32, value: u32) -> Self {
        let dec = Button::with_icon(theme::ICON_MINUS)
            .styled(theme::button_keyboard())
            .with_radius(12);
        let inc = Button::with_icon(theme::ICON_PLUS)
            .styled(theme::button_keyboard())
            .with_radius(12);
        let value = value.clamp(min, max);
        Self {
            area: Rect::zero(),
            dec: Maybe::new(theme::BG, dec, value > min),
            inc: Maybe::new(theme::BG, inc, value < max),
            min,
            max,
            value,
        }
    }

    fn increase(&mut self, ctx: &mut EventCtx) {
        self.value = self.value.saturating_add(1).min(self.max);
        self.on_change(ctx);
    }

    fn decrease(&mut self, ctx: &mut EventCtx) {
        self.value = self.value.saturating_sub(1).max(self.min);
        self.on_change(ctx);
    }

    fn on_change(&mut self, ctx: &mut EventCtx) {
        self.dec.show_if(ctx, self.value > self.min);
        self.inc.show_if(ctx, self.value < self.max);
        ctx.request_paint();
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

        if let Some(text) = strutil::format_i64(self.value as i64, &mut buf) {
            let font = fonts::FONT_SATOSHI_EXTRALIGHT_72;
            let y_offset = Offset::y(font.visible_text_height(text) / 2);
            shape::Text::new(self.area.center().ofs(y_offset), text, font)
                .with_align(Alignment::Center)
                .with_fg(theme::GREY)
                .render(target);
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
        if let Some(ButtonMsg::Clicked) = self.dec.event(ctx, event) {
            self.decrease(ctx);
        };
        if let Some(ButtonMsg::Clicked) = self.inc.event(ctx, event) {
            self.increase(ctx);
        };
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
}
