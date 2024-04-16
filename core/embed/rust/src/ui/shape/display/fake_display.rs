use crate::ui::{
    display::Color,
    geometry::Rect,
    shape::{DirectRenderer, Mono8Canvas},
};

pub fn render_on_display<'a, F>(_clip: Option<Rect>, _bg_color: Option<Color>, _func: F)
where
    F: FnOnce(&mut DirectRenderer<'_, 'a, Mono8Canvas<'a>>),
{
    panic!("Not implemented")
}
