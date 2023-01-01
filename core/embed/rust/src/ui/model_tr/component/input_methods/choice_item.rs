use crate::ui::{
    display::{rect_fill, rect_fill_corners, rect_outline_rounded, Font, Icon},
    geometry::{Offset, Rect},
    model_tr::theme,
};
use heapless::String;

use super::super::{
    common::{display, display_inverse, display_right},
    ButtonDetails, ButtonLayout, Choice,
};

/// Simple string component used as a choice item.
#[derive(Clone)]
pub struct ChoiceItem {
    text: String<50>,
    icon: Option<Icon>,
    btn_layout: ButtonLayout,
    font: Font,
}

impl ChoiceItem {
    pub fn new<T>(text: T, btn_layout: ButtonLayout) -> Self
    where
        T: AsRef<str>,
    {
        Self {
            text: String::from(text.as_ref()),
            icon: None,
            btn_layout,
            font: theme::FONT_CHOICE_ITEMS,
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

    /// Getting the text width in pixels.
    pub fn text_width(&self) -> i16 {
        self.font.text_width(&self.text)
    }

    /// Getting the non-central width in pixels.
    /// It will show an icon if defined, otherwise the text, not both.
    pub fn width_side(&self) -> i16 {
        if let Some(icon) = self.icon {
            icon.width()
        } else {
            self.text_width()
        }
    }

    /// Whether the whole item fits into the given rectangle.
    pub fn fits(&self, rect: Rect) -> bool {
        self.width_side() <= rect.width()
    }

    /// Draws highlight around this choice item.
    /// Must be called before the item is drawn, otherwise it will
    /// cover the item.
    pub fn paint_rounded_highlight(&self, area: Rect, inverse: bool) {
        let bound = 3;
        let left_bottom =
            area.bottom_center() + Offset::new(-self.width_center() / 2 - bound, bound + 1);
        let outline_size = Offset::new(
            self.width_center() + 2 * bound,
            self.font.text_height() + 2 * bound,
        );
        let outline = Rect::from_bottom_left_and_size(left_bottom, outline_size);
        if inverse {
            rect_fill(outline, theme::FG);
            rect_fill_corners(outline, theme::BG);
        } else {
            rect_outline_rounded(outline, theme::FG, theme::BG, 1);
        }
    }

    /// Painting the item as a choice on the left side from center.
    /// Showing only the icon, if available, otherwise the text.
    pub fn render_left(&self, area: Rect) {
        if let Some(icon) = self.icon {
            icon.draw_bottom_right(area.bottom_right(), theme::FG, theme::BG);
        } else {
            display_right(area.bottom_right(), &self.text, self.font);
        }
    }

    /// Painting the item as a choice on the right side from center.
    /// Showing only the icon, if available, otherwise the text.
    pub fn render_right(&self, area: Rect) {
        if let Some(icon) = self.icon {
            icon.draw_bottom_left(area.bottom_left(), theme::FG, theme::BG);
        } else {
            display(area.bottom_left(), &self.text, self.font);
        }
    }

    /// Setting left button.
    pub fn set_left_btn(&mut self, btn_left: Option<ButtonDetails>) {
        self.btn_layout.btn_left = btn_left;
    }

    /// Setting middle button.
    pub fn set_middle_btn(&mut self, btn_middle: Option<ButtonDetails>) {
        self.btn_layout.btn_middle = btn_middle;
    }

    /// Setting right button.
    pub fn set_right_btn(&mut self, btn_right: Option<ButtonDetails>) {
        self.btn_layout.btn_right = btn_right;
    }

    /// Changing the text.
    pub fn set_text(&mut self, text: String<50>) {
        self.text = text;
    }
}

impl Choice for ChoiceItem {
    /// Painting the item as the main choice in the middle.
    /// Showing both the icon and text, if the icon is available.
    fn paint_center(&self, area: Rect, inverse: bool) {
        self.paint_rounded_highlight(area, inverse);

        let mut baseline = area.bottom_center() + Offset::x(-self.width_center() / 2);
        if let Some(icon) = self.icon {
            let fg_color = if inverse { theme::BG } else { theme::FG };
            let bg_color = if inverse { theme::FG } else { theme::BG };
            icon.draw_bottom_left(baseline, fg_color, bg_color);
            baseline = baseline + Offset::x(icon.width() + 2);
        }
        if inverse {
            display_inverse(baseline, &self.text, self.font);
        } else {
            display(baseline, &self.text, self.font);
        }
    }

    /// Getting the overall width in pixels when displayed in center.
    /// That means both the icon and text will be shown.
    fn width_center(&self) -> i16 {
        let icon_width = if let Some(icon) = self.icon {
            icon.width() + 2
        } else {
            0
        };
        self.text_width() + icon_width
    }

    /// Painting item on the side if it fits, otherwise paint incomplete if
    /// allowed
    fn paint_left(&self, area: Rect, show_incomplete: bool) -> Option<i16> {
        // When the item does not fit, we stop.
        // Rendering the item anyway if the incomplete items are allowed.
        if !self.fits(area) {
            if show_incomplete {
                self.render_left(area);
            }
            return None;
        }

        // Rendering the item.
        self.render_left(area);

        Some(self.width_side())
    }

    /// Painting item on the side if it fits, otherwise paint incomplete if
    /// allowed
    fn paint_right(&self, area: Rect, show_incomplete: bool) -> Option<i16> {
        // When the item does not fit, we stop.
        // Rendering the item anyway if the incomplete items are allowed.
        if !self.fits(area) {
            if show_incomplete {
                self.render_right(area);
            }
            return None;
        }

        // Rendering the item.
        self.render_right(area);

        Some(self.width_side())
    }

    /// Getting current button layout.
    fn btn_layout(&self) -> ButtonLayout {
        self.btn_layout.clone()
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for ChoiceItem {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.open("ChoiceItem");
        t.content_flag();
        t.string(&self.text);
        t.content_flag();
        t.close();
    }
}
