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
    component::{Button, ButtonContent, ButtonMsg},
    constant, theme,
};

const BUTTON_EXPAND_BORDER: i16 = 32;

/// Component for the header of a screen. Reduced variant for Bootloader UI.
pub struct BldHeader<'a> {
    area: Rect,
    title: Label<'a>,
    /// button in the top-right corner
    right_button: Option<Button>,
    /// button in the top-left corner
    left_button: Option<Button>,
    right_button_msg: BldHeaderMsg,
    left_button_msg: BldHeaderMsg,
    /// icon in the top-left corner (used instead of left button)
    icon: Option<Icon>,
    icon_color: Option<Color>,
}

#[derive(Copy, Clone)]
pub enum BldHeaderMsg {
    Back,
    Cancelled,
    Menu,
    Info,
}

impl<'a> BldHeader<'a> {
    pub const HEADER_HEIGHT: i16 = theme::HEADER_HEIGHT; // [px]
    pub const HEADER_BUTTON_WIDTH: i16 = 56; // [px]
    const HEADER_INSETS: Insets = theme::SIDE_INSETS; // [px]

    pub const fn new(title: TString<'a>) -> Self {
        Self {
            area: Rect::zero(),
            title: Label::left_aligned(
                title,
                theme::bootloader::text_title(theme::bootloader::BLD_BG),
            )
            .vertically_centered(),
            right_button: None,
            left_button: None,
            right_button_msg: BldHeaderMsg::Cancelled,
            left_button_msg: BldHeaderMsg::Cancelled,
            icon: None,
            icon_color: None,
        }
    }

    pub fn new_rsod_header() -> Self {
        Self::new("Failure".into()).with_icon(theme::ICON_INFO, theme::RED)
    }

    pub fn new_pay_attention() -> Self {
        Self::new("Pay attention".into()).with_icon(theme::ICON_WARNING, theme::GREY)
    }

    #[inline(never)]
    pub fn with_right_button(self, button: Button, msg: BldHeaderMsg) -> Self {
        debug_assert!(matches!(button.content(), ButtonContent::Icon(_)));
        let touch_area = Insets::uniform(BUTTON_EXPAND_BORDER);
        Self {
            right_button: Some(button.with_expanded_touch_area(touch_area)),
            right_button_msg: msg,
            ..self
        }
    }

    #[inline(never)]
    pub fn with_left_button(self, button: Button, msg: BldHeaderMsg) -> Self {
        debug_assert!(matches!(button.content(), ButtonContent::Icon(_)));
        let touch_area = Insets::uniform(BUTTON_EXPAND_BORDER);
        Self {
            icon: None,
            left_button: Some(button.with_expanded_touch_area(touch_area)),
            left_button_msg: msg,
            ..self
        }
    }

    #[inline(never)]
    pub fn with_menu_button(self) -> Self {
        self.with_right_button(
            Button::with_icon(theme::ICON_MENU).styled(theme::bootloader::button_header()),
            BldHeaderMsg::Menu,
        )
    }

    #[inline(never)]
    pub fn with_close_button(self) -> Self {
        self.with_right_button(
            Button::with_icon(theme::ICON_CLOSE).styled(theme::bootloader::button_header()),
            BldHeaderMsg::Cancelled,
        )
    }

    #[inline(never)]
    pub fn with_icon(self, icon: Icon, color: Color) -> Self {
        Self {
            left_button: None,
            icon: Some(icon),
            icon_color: Some(color),
            ..self
        }
    }

    /// Calculates the width needed for the left icon, be it a button with icon
    /// or just icon
    fn left_icon_width(&self) -> i16 {
        let margin_right: i16 = 16; // [px]
        if let Some(b) = &self.left_button {
            match b.content() {
                ButtonContent::Icon(icon) => icon.toif.width() + margin_right,
                _ => 0,
            }
        } else if let Some(icon) = self.icon {
            icon.toif.width() + margin_right
        } else {
            0
        }
    }
}

impl<'a> Component for BldHeader<'a> {
    type Msg = BldHeaderMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        debug_assert_eq!(bounds.width(), constant::screen().width());
        debug_assert_eq!(bounds.height(), Self::HEADER_HEIGHT);

        let bounds = bounds.inset(Self::HEADER_INSETS);
        let rest = if let Some(b) = &mut self.right_button {
            let (rest, button_area) = bounds.split_right(Self::HEADER_BUTTON_WIDTH);
            b.place(button_area);
            rest
        } else {
            bounds
        };

        let icon_width = self.left_icon_width();
        let (rest, title_area) = rest.split_left(icon_width);

        self.left_button.place(rest);
        self.title.place(title_area);
        self.area = bounds;
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if let Some(ButtonMsg::Clicked) = self.left_button.event(ctx, event) {
            return Some(self.left_button_msg);
        };
        if let Some(ButtonMsg::Clicked) = self.right_button.event(ctx, event) {
            return Some(self.right_button_msg);
        };

        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.right_button.render(target);
        self.left_button.render(target);
        if let Some(icon) = self.icon {
            shape::ToifImage::new(self.area.left_center(), icon.toif)
                .with_fg(self.icon_color.unwrap_or(theme::GREY_LIGHT))
                .with_align(Alignment2D::CENTER_LEFT)
                .render(target);
        }
        self.title.render(target);
    }
}
