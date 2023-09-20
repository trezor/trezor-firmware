use crate::{
    strutil::{ShortString, StringType},
    ui::{
        display::{self, rect_fill, rect_fill_corners, rect_outline_rounded, Font, Icon},
        geometry::{Alignment2D, Offset, Rect},
    },
};

use heapless::String;

use super::super::{theme, ButtonDetails, ButtonLayout, Choice};

const ICON_RIGHT_PADDING: i16 = 2;

/// Simple string component used as a choice item.
#[derive(Clone)]
pub struct ChoiceItem<T: StringType> {
    text: ShortString,
    icon: Option<Icon>,
    btn_layout: ButtonLayout<T>,
    font: Font,
    middle_action_without_release: bool,
}

impl<T: StringType> ChoiceItem<T> {
    pub fn new<U: AsRef<str>>(text: U, btn_layout: ButtonLayout<T>) -> Self {
        Self {
            text: String::from(text.as_ref()),
            icon: None,
            btn_layout,
            font: theme::FONT_CHOICE_ITEMS,
            middle_action_without_release: false,
        }
    }

    /// Allows to add the icon.
    pub fn with_icon(mut self, icon: Icon) -> Self {
        self.icon = Some(icon);
        self
    }

    /// Allows to change the font.
    pub fn with_font(mut self, font: Font) -> Self {
        self.font = font;
        self
    }

    /// Allows for middle action without release.
    pub fn with_middle_action_without_release(mut self) -> Self {
        self.middle_action_without_release = true;
        if let Some(middle) = self.btn_layout.btn_middle.as_mut() {
            middle.send_long_press = true;
        }
        self
    }

    /// Setting left button.
    pub fn set_left_btn(&mut self, btn_left: Option<ButtonDetails<T>>) {
        self.btn_layout.btn_left = btn_left;
    }

    /// Setting middle button.
    pub fn set_middle_btn(&mut self, btn_middle: Option<ButtonDetails<T>>) {
        self.btn_layout.btn_middle = btn_middle;
    }

    /// Setting right button.
    pub fn set_right_btn(&mut self, btn_right: Option<ButtonDetails<T>>) {
        self.btn_layout.btn_right = btn_right;
    }

    /// Changing the text.
    pub fn set_text(&mut self, text: ShortString) {
        self.text = text;
    }

    fn side_text(&self) -> Option<&str> {
        if self.icon.is_some() {
            None
        } else {
            Some(self.text.as_ref())
        }
    }

    pub fn content(&self) -> &str {
        self.text.as_ref()
    }
}

impl<T> Choice<T> for ChoiceItem<T>
where
    T: StringType + Clone,
{
    /// Painting the item as the main choice in the middle.
    /// Showing both the icon and text, if the icon is available.
    fn paint_center(&self, area: Rect, inverse: bool) {
        let width = text_icon_width(Some(self.text.as_ref()), self.icon, self.font);
        paint_rounded_highlight(area, Offset::new(width, self.font.text_height()), inverse);
        paint_text_icon(
            area,
            width,
            Some(self.text.as_ref()),
            self.icon,
            self.font,
            inverse,
        );
    }

    /// Getting the overall width in pixels when displayed in center.
    /// That means both the icon and text will be shown.
    fn width_center(&self) -> i16 {
        text_icon_width(Some(self.text.as_ref()), self.icon, self.font)
    }

    /// Getting the non-central width in pixels.
    /// It will show an icon if defined, otherwise the text, not both.
    fn width_side(&self) -> i16 {
        text_icon_width(self.side_text(), self.icon, self.font)
    }

    /// Painting smaller version of the item on the side.
    fn paint_side(&self, area: Rect) {
        let width = text_icon_width(self.side_text(), self.icon, self.font);
        paint_text_icon(area, width, self.side_text(), self.icon, self.font, false);
    }

    /// Getting current button layout.
    fn btn_layout(&self) -> ButtonLayout<T> {
        self.btn_layout.clone()
    }

    /// Whether to do middle action without release
    fn trigger_middle_without_release(&self) -> bool {
        self.middle_action_without_release
    }
}

fn paint_rounded_highlight(area: Rect, size: Offset, inverse: bool) {
    let bound = theme::BUTTON_OUTLINE;
    let left_bottom = area.bottom_center() + Offset::new(-size.x / 2 - bound, bound + 1);
    let x_size = size.x + 2 * bound;
    let y_size = size.y + 2 * bound;
    let outline_size = Offset::new(x_size, y_size);
    let outline = Rect::from_bottom_left_and_size(left_bottom, outline_size);
    if inverse {
        rect_fill(outline, theme::FG);
        rect_fill_corners(outline, theme::BG);
    } else {
        rect_outline_rounded(outline, theme::FG, theme::BG, 1);
    }
}

fn text_icon_width(text: Option<&str>, icon: Option<Icon>, font: Font) -> i16 {
    match (text, icon) {
        (Some(text), Some(icon)) => {
            icon.toif.width() + ICON_RIGHT_PADDING + font.visible_text_width(text)
        }
        (Some(text), None) => font.visible_text_width(text),
        (None, Some(icon)) => icon.toif.width(),
        (None, None) => 0,
    }
}

fn paint_text_icon(
    area: Rect,
    width: i16,
    text: Option<&str>,
    icon: Option<Icon>,
    font: Font,
    inverse: bool,
) {
    let fg_color = if inverse { theme::BG } else { theme::FG };
    let bg_color = if inverse { theme::FG } else { theme::BG };

    let mut baseline = area.bottom_center() - Offset::x(width / 2);
    if let Some(icon) = icon {
        let height_diff = font.text_height() - icon.toif.height();
        let vertical_offset = Offset::y(-height_diff / 2);
        icon.draw(
            baseline + vertical_offset,
            Alignment2D::BOTTOM_LEFT,
            fg_color,
            bg_color,
        );
        baseline = baseline + Offset::x(icon.toif.width() + ICON_RIGHT_PADDING);
    }

    if let Some(text) = text {
        // Possibly shifting the baseline left, when there is a text bearing.
        // This is to center the text properly.
        baseline = baseline - Offset::x(font.start_x_bearing(text));
        display::text_left(baseline, text, font, fg_color, bg_color);
    }
}

// DEBUG-ONLY SECTION BELOW

#[cfg(feature = "ui_debug")]
impl<T: StringType> crate::trace::Trace for ChoiceItem<T> {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("ChoiceItem");
        t.string("content", self.text.as_ref());
    }
}
