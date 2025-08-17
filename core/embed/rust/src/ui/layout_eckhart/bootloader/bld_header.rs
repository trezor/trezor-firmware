use crate::{
    strutil::TString,
    ui::{
        component::{Component, Event, EventCtx, Label},
        display::{Color, Icon},
        geometry::{Alignment2D, Insets, Rect},
        shape::{self, Renderer},
    },
};

use super::super::{
    component::{Button, ButtonContent, ButtonMsg, FuelGauge},
    constant,
    theme::{self, bootloader::text_title},
};

const BUTTON_EXPAND_BORDER: i16 = 32;

/// Component for the header of a screen. Reduced variant for Bootloader UI.
pub struct BldHeader<'a> {
    area: Rect,
    left_content: LeftContent<'a>,
    /// Button in the top-right corner
    right_button: Option<Button>,
    right_button_msg: BldHeaderMsg,
}

#[derive(Copy, Clone)]
pub enum BldHeaderMsg {
    Back,
    Cancelled,
    Menu,
    Info,
}

enum LeftContent<'a> {
    /// Title with indication of charging on the left
    Title(Label<'a>, FuelGauge),
    /// Icon and title
    IconAndTitle(Label<'a>, Icon, Color),
    /// Battery status indicator (icon, percentage) and nothing else
    FuelGauge(FuelGauge),
}

impl<'a> BldHeader<'a> {
    pub const HEADER_HEIGHT: i16 = theme::HEADER_HEIGHT; // [px]
    pub const HEADER_BUTTON_WIDTH: i16 = 56; // [px]
    const HEADER_INSETS: Insets = theme::SIDE_INSETS; // [px]

    pub const fn new(title: TString<'a>) -> Self {
        Self::from_left_content(LeftContent::Title(
            Label::left_aligned(title, text_title(theme::GREY)).vertically_centered(),
            FuelGauge::charging_icon_only(),
        ))
    }

    pub fn new_done(color: Color) -> Self {
        Self::from_left_content(LeftContent::IconAndTitle(
            Label::left_aligned("Done".into(), text_title(color)).vertically_centered(),
            theme::ICON_DONE,
            color,
        ))
    }

    pub fn new_important() -> Self {
        Self::from_left_content(LeftContent::IconAndTitle(
            Label::left_aligned("Important".into(), text_title(theme::RED)).vertically_centered(),
            theme::ICON_WARNING,
            theme::RED,
        ))
    }

    pub const fn new_with_fuel_gauge() -> Self {
        Self::from_left_content(LeftContent::FuelGauge(FuelGauge::always()))
    }

    #[inline(never)]
    pub const fn with_right_button(self, button: Button, msg: BldHeaderMsg) -> Self {
        debug_assert!(matches!(button.content(), ButtonContent::Icon(_)));
        let touch_area = Insets::uniform(BUTTON_EXPAND_BORDER);
        Self {
            right_button: Some(button.with_expanded_touch_area(touch_area)),
            right_button_msg: msg,
            ..self
        }
    }

    #[inline(never)]
    pub const fn with_menu_button(self) -> Self {
        self.with_right_button(
            Button::with_icon(theme::ICON_MENU).styled(theme::bootloader::button_header()),
            BldHeaderMsg::Menu,
        )
    }

    #[inline(never)]
    pub const fn with_close_button(self) -> Self {
        self.with_right_button(
            Button::with_icon(theme::ICON_CLOSE).styled(theme::bootloader::button_header()),
            BldHeaderMsg::Cancelled,
        )
    }

    const fn from_left_content(left_content: LeftContent<'a>) -> Self {
        Self {
            area: Rect::zero(),
            left_content,
            right_button: None,
            right_button_msg: BldHeaderMsg::Cancelled,
        }
    }

    fn place_components(&mut self, bounds: Rect) {
        let bounds = if let Some(b) = &mut self.right_button {
            let (rest, right_button_area) = bounds.split_right(Self::HEADER_BUTTON_WIDTH);
            b.place(right_button_area);
            rest
        } else {
            bounds
        };
        match &mut self.left_content {
            LeftContent::Title(label, fuel_gauge) => {
                if fuel_gauge.should_be_shown() {
                    // we know that FuelGauge for this content shows only charging icon
                    let icon_width = Self::left_icon_width(&theme::ICON_BATTERY_ZAP);
                    let (icon_area, title_area) = bounds.split_left(icon_width);
                    label.place(title_area);
                    fuel_gauge.place(icon_area);
                } else {
                    label.place(bounds);
                }
            }
            LeftContent::IconAndTitle(label, icon, _) => {
                let icon_width = Self::left_icon_width(icon);
                let (_, title_area) = bounds.split_left(icon_width);
                label.place(title_area);
            }
            LeftContent::FuelGauge(fuel_gauge) => {
                fuel_gauge.place(bounds);
            }
        };
    }

    /// Calculates the width needed for the left icon
    fn left_icon_width(icon: &Icon) -> i16 {
        const ICON_TEXT_GAP: i16 = 16;
        icon.toif.width() + ICON_TEXT_GAP
    }
}

impl<'a> Component for BldHeader<'a> {
    type Msg = BldHeaderMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        debug_assert_eq!(bounds.width(), constant::screen().width());
        debug_assert_eq!(bounds.height(), Self::HEADER_HEIGHT);

        let bounds = bounds.inset(Self::HEADER_INSETS);
        self.area = bounds;
        self.place_components(bounds);
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if let Some(ButtonMsg::Clicked) = self.right_button.event(ctx, event) {
            return Some(self.right_button_msg);
        };
        match &mut self.left_content {
            LeftContent::Title(_, fuel_gauge) => {
                match event {
                    Event::Attach(..) | Event::PM(..) => {
                        fuel_gauge.event(ctx, event);
                        self.place_components(self.area);
                    }
                    _ => {}
                };
            }
            LeftContent::FuelGauge(fuel_gauge) => {
                fuel_gauge.event(ctx, event);
            }
            _ => {}
        }

        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        match &self.left_content {
            LeftContent::Title(label, fuel_gauge) => {
                label.render(target);
                if !label.text().is_empty() {
                    // this prevents overlapping icon with the text on WelcomeScreen, it's better
                    // to not show it there
                    fuel_gauge.render(target);
                }
            }
            LeftContent::IconAndTitle(label, icon, color) => {
                label.render(target);
                shape::ToifImage::new(self.area.left_center(), icon.toif)
                    .with_fg(*color)
                    .with_align(Alignment2D::CENTER_LEFT)
                    .render(target);
            }
            LeftContent::FuelGauge(fuel_gauge) => {
                fuel_gauge.render(target);
            }
        };
        self.right_button.render(target);
    }
}
