use crate::ui::{
    display::Color,
    shape::{render::ScopedRenderer, DirectRenderer, Mono8Canvas, Viewport},
};

pub type ConcreteRenderer<'a, 'alloc> = DirectRenderer<'a, 'alloc, Mono8Canvas<'alloc>>;

pub fn render_on_display<'env, F>(_viewport: Option<Viewport>, _bg_color: Option<Color>, _func: F)
where
    F: for<'alloc> FnOnce(&mut ScopedRenderer<'alloc, 'env, ConcreteRenderer<'_, 'alloc>>),
{
    unimplemented!();
}
