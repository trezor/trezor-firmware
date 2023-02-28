use crate::ui::{
    constant::{screen, LOADER_INNER},
    display,
    display::{Color, Icon},
    geometry::{Offset, Rect},
};

pub fn loader_rectangular(
    progress: u16,
    y_offset: i16,
    fg_color: Color,
    bg_color: Color,
    icon: Option<(Icon, Color)>,
) {
    let area = Rect::from_center_and_size(screen().center(), Offset::uniform(LOADER_INNER as _))
        .translate(Offset::y(y_offset));

    display::rect_rounded2_partial(
        area,
        fg_color,
        bg_color,
        (100 * progress as u32 / 1000) as i16,
        icon,
    );
}
