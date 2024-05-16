use crate::ui::{
    display::Color,
    shape::{DirectRenderer, Mono8Canvas, Viewport},
};

pub fn render_on_display<F>(_viewport: Option<Viewport>, _bg_color: Option<Color>, _func: F)
where
    F: for<'a> FnOnce(&mut DirectRenderer<'_, 'a, Mono8Canvas<'a>>),
{
    unimplemented!();
}
