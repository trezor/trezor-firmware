use crate::{
    strutil::ShortString,
    ui::{
        component::text::{layout::Lines, TextStyle},
        constant::screen,
        display::Icon,
        geometry::{Alignment2D, Offset, Point, Rect},
        shape::{self, Renderer},
    },
};

use heapless::{String, Vec};

use super::super::{theme, ButtonDetails, ButtonLayout, Choice};

const ICON_RIGHT_PADDING: i16 = 2;

/// Simple string component used as a choice item.
#[derive(Clone)]
pub struct ChoiceItem {
    text: ShortString,
    icon: Option<Icon>,
    btn_layout: ButtonLayout,
    style: &'static TextStyle,
    middle_action_without_release: bool,
}

impl ChoiceItem {
    pub fn new<U: AsRef<str>>(text: U, btn_layout: ButtonLayout) -> Self {
        Self {
            text: unwrap!(String::try_from(text.as_ref())),
            icon: None,
            btn_layout,
            style: &theme::TEXT_CHOICE_ITEMS,
            middle_action_without_release: false,
        }
    }

    /// Allows to add the icon.
    pub fn with_icon(mut self, icon: Icon) -> Self {
        self.icon = Some(icon);
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
        let text_area = Rect::from_center_and_size(area.center(), self.size_center());

        render_rounded_highlight(target, text_area, inverse);
        render_text_icon(
            target,
            text_area,
            Some(self.text.as_ref()),
            self.icon,
            self.style,
            inverse,
        );
    }

    /// Painting smaller version of the item on the side.
    fn render_side<'s>(&self, target: &mut impl Renderer<'s>, area: Rect) {
        let text_area = area.split_center_by_height(self.size_side().y).1;

        render_text_icon(
            target,
            text_area,
            self.side_text(),
            self.icon,
            self.style,
            false,
        );
    }

    /// Getting the overall size in pixels when displayed in center.
    /// That means both the icon and text will be shown.
    fn size_center(&self) -> Offset {
        text_icon_size(Some(self.text.as_ref()), self.icon, self.style)
    }

    /// Getting the non-central size in pixels.
    /// It will show an icon if defined, otherwise the text, not both.
    fn size_side(&self) -> Offset {
        text_icon_size(self.side_text(), self.icon, self.style)
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

fn render_rounded_highlight<'s>(target: &mut impl Renderer<'s>, area: Rect, inverse: bool) {
    let outline_size = area.size() + Offset::uniform(2 * theme::BUTTON_OUTLINE);
    let center = area.center() + Offset::y(1);
    let outline = Rect::from_center_and_size(center, outline_size);
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

struct TextRows<'s> {
    rows: Vec<&'s str, 3>,
    size: Offset,
}

impl<'s> TextRows<'s> {
    fn new(text: &'s str, max_width: i16, style: &TextStyle) -> Self {
        let font = style.text_font;
        let mut rows = Vec::new();
        let row_height = font.allcase_text_height();
        let mut size = Offset::zero();
        let mut first = true;
        for line in Lines::split(text, max_width, font) {
            unwrap!(rows.push(line));
            size.x = size.x.max(font.visible_text_width(line));
            size.y += row_height + if first { 0 } else { style.line_spacing };
            first = false;
        }
        Self { rows, size }
    }
}

const MAX_TEXT_WIDTH: i16 = screen().width() - 10;

fn text_icon_size(text: Option<&str>, icon: Option<Icon>, style: &TextStyle) -> Offset {
    let text_size = text.map(|text| TextRows::new(text, MAX_TEXT_WIDTH, style).size);
    let icon_size = icon.map(|icon| icon.toif.size());

    let padding = match (text_size, icon_size) {
        (Some(_), Some(_)) => ICON_RIGHT_PADDING,
        _ => 0,
    };

    let text_size = text_size.unwrap_or(Offset::zero());
    let icon_size = icon_size.unwrap_or(Offset::zero());
    Offset::new(
        text_size.x + padding + icon_size.x,
        text_size.y.max(style.text_font.allcase_text_height()),
    )
}

fn render_text_icon<'s>(
    target: &mut impl Renderer<'s>,
    area: Rect,
    text: Option<&str>,
    icon: Option<Icon>,
    style: &TextStyle,
    inverse: bool,
) {
    let font = style.text_font;
    let fg_color = if inverse { theme::BG } else { theme::FG };
    let width = area.width();
    let row_height = font.allcase_text_height();

    let mut center_left = area.center() - Offset::x(width / 2);
    if let Some(icon) = icon {
        shape::ToifImage::new(center_left, icon.toif)
            .with_align(Alignment2D::CENTER_LEFT)
            .with_fg(fg_color)
            .render(target);

        center_left.x += icon.toif.width() + ICON_RIGHT_PADDING;
    }

    if let Some(text) = text {
        let mut baseline = Point::new(center_left.x, area.top_left().y);
        let text_rows = TextRows::new(text, MAX_TEXT_WIDTH, style);
        for row in text_rows.rows {
            baseline = baseline + Offset::y(row_height);
            // Possibly shifting the baseline left, when there is a text bearing.
            // This is to center the text properly.
            let center_offset = Offset::x(
                (text_rows.size.x - font.visible_text_width(row)) / 2 - font.start_x_bearing(row),
            );
            shape::Text::new(baseline + center_offset, row, font)
                .with_fg(fg_color)
                .render(target);
            baseline = baseline + Offset::y(style.line_spacing);
        }
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
