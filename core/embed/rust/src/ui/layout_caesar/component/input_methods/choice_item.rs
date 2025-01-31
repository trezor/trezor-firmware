use crate::{
    strutil::ShortString,
    ui::{
        display::{Font, Icon},
        geometry::{Alignment2D, Offset, Rect},
        shape,
        shape::Renderer,
    },
};

use heapless::String;

use super::super::{theme, ButtonDetails, ButtonLayout, Choice};

const ICON_RIGHT_PADDING: i16 = 2;

/// Simple string component used as a choice item.
#[derive(Clone)]
pub struct ChoiceItem {
    text: ShortString,
    icon: Option<Icon>,
    btn_layout: ButtonLayout,
    font: Font,
    middle_action_without_release: bool,
}

impl ChoiceItem {
    pub fn new<U: AsRef<str>>(text: U, btn_layout: ButtonLayout) -> Self {
        Self {
            text: unwrap!(String::try_from(text.as_ref())),
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

impl Choice for ChoiceItem {
    /// Painting the item as the main choice in the middle.
    /// Showing both the icon and text, if the icon is available.
    fn render_center<'s>(&self, target: &mut impl Renderer<'s>, area: Rect, inverse: bool) {
        let width = text_icon_width(Some(self.text.as_ref()), self.icon, self.font);
        render_rounded_highlight(
            target,
            area,
            Offset::new(width, self.font.visible_text_height("Ay")),
            inverse,
        );
        render_text_icon(
            target,
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
    fn render_side<'s>(&self, target: &mut impl Renderer<'s>, area: Rect) {
        let width = text_icon_width(self.side_text(), self.icon, self.font);
        render_text_icon(
            target,
            area,
            width,
            self.side_text(),
            self.icon,
            self.font,
            false,
        );
    }

    /// Getting current button layout.
    fn btn_layout(&self) -> ButtonLayout {
        self.btn_layout.clone()
    }

    /// Whether to do middle action without release
    fn trigger_middle_without_release(&self) -> bool {
        self.middle_action_without_release
    }
}

fn render_rounded_highlight<'s>(
    target: &mut impl Renderer<'s>,
    area: Rect,
    size: Offset,
    inverse: bool,
) {
    let bound = theme::BUTTON_OUTLINE;
    let left_bottom = area.bottom_center() + Offset::new(-size.x / 2 - bound, bound + 1);
    let x_size = size.x + 2 * bound;
    let y_size = size.y + 2 * bound;
    let outline_size = Offset::new(x_size, y_size);
    let outline = Rect::from_bottom_left_and_size(left_bottom, outline_size);
    if inverse {
        shape::Bar::new(outline)
            .with_radius(1)
            .with_bg(theme::FG)
            .render(target);
    } else {
        // Draw outline by drawing two rounded rectangles
        shape::Bar::new(outline)
            .with_radius(1)
            .with_bg(theme::FG)
            .render(target);

        shape::Bar::new(outline.shrink(1))
            .with_radius(1)
            .with_bg(theme::BG)
            .render(target);
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

fn render_text_icon<'s>(
    target: &mut impl Renderer<'s>,
    area: Rect,
    width: i16,
    text: Option<&str>,
    icon: Option<Icon>,
    font: Font,
    inverse: bool,
) {
    let fg_color = if inverse { theme::BG } else { theme::FG };

    let mut baseline = area.bottom_center() - Offset::x(width / 2);
    if let Some(icon) = icon {
        let height_diff = font.visible_text_height("Ay") - icon.toif.height();
        let vertical_offset = Offset::y(-height_diff / 2);
        shape::ToifImage::new(baseline + vertical_offset, icon.toif)
            .with_align(Alignment2D::BOTTOM_LEFT)
            .with_fg(fg_color)
            .render(target);

        baseline = baseline + Offset::x(icon.toif.width() + ICON_RIGHT_PADDING);
    }

    if let Some(text) = text {
        // Possibly shifting the baseline left, when there is a text bearing.
        // This is to center the text properly.
        baseline = baseline - Offset::x(font.start_x_bearing(text));
        shape::Text::new(baseline, text, font)
            .with_fg(fg_color)
            .render(target);
    }
}

// DEBUG-ONLY SECTION BELOW

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for ChoiceItem {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("ChoiceItem");
        t.string("content", self.text.as_str().into());
    }
}
